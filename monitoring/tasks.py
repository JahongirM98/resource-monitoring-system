# monitoring/tasks.py
import logging
import requests
from datetime import timedelta
from django.utils import timezone
from celery import shared_task
from .models import Machine, Metric, Incident

logger = logging.getLogger(__name__)

# Интервалы и окна анализа
SAMPLE_INTERVAL_MIN = 15
MEM_WINDOW_MIN = 30
DISK_WINDOW_MIN = 120


@shared_task
def schedule_fetch_all():
    """
    Фоновый сбор метрик с машин.
    Каждые 15 минут Celery Beat вызывает эту задачу.
    """
    machines = Machine.objects.filter(active=True).only("id", "endpoint")
    logger.info("schedule_fetch_all: %s machines", machines.count())

    with requests.Session() as session:
        for m in machines:
            try:
                resp = session.get(m.endpoint, timeout=10)
                if resp.status_code != 200:
                    logger.warning("non-200 from %s: %s", m.endpoint, resp.status_code)
                    continue

                data = resp.json()
                cpu = int(data.get("cpu", 0))
                mem = float(str(data.get("mem", "0")).rstrip("%"))
                disk = float(str(data.get("disk", "0")).rstrip("%"))
                uptime = str(data.get("uptime", ""))

                Metric.objects.create(
                    machine=m,
                    cpu=cpu,
                    mem_percent=mem,
                    disk_percent=disk,
                    uptime=uptime,
                )
                logger.info("saved metric for %s", m.name)

            except Exception as e:
                logger.exception("fetch error for %s: %s", m.endpoint, e)


# ----------------------- Инциденты -----------------------

def _get_or_none_active_incident(machine_id, itype):
    return Incident.objects.filter(machine_id=machine_id, type=itype, is_active=True).first()


def _open_incident(machine_id, itype, details=None):
    Incident.objects.create(machine_id=machine_id, type=itype, is_active=True, details=details or {})
    logger.info("Incident OPEN: %s on machine %s", itype, machine_id)


def _touch_incident(incident: Incident):
    incident.save(update_fields=["last_seen_at"])


def _resolve_incident(incident: Incident):
    if incident and incident.is_active:
        incident.is_active = False
        incident.resolved_at = timezone.now()
        incident.save(update_fields=["is_active", "resolved_at"])
        logger.info("Incident RESOLVED: %s on machine %s", incident.type, incident.machine_id)


def _mem_required_samples():
    return max(2, MEM_WINDOW_MIN // SAMPLE_INTERVAL_MIN)


def _disk_required_samples():
    return max(2, DISK_WINDOW_MIN // SAMPLE_INTERVAL_MIN)


def _check_cpu_rule(machine_id):
    latest = Metric.objects.filter(machine_id=machine_id).order_by("-received_at").first()
    itype = Incident.Type.CPU_HIGH
    active = _get_or_none_active_incident(machine_id, itype)

    if latest and latest.cpu > 85:
        if not active:
            _open_incident(machine_id, itype, {"cpu": latest.cpu, "at": latest.received_at.isoformat()})
        else:
            _touch_incident(active)
    else:
        if active:
            _resolve_incident(active)


def _check_mem_rule(machine_id):
    N = _mem_required_samples()
    qs = Metric.objects.filter(machine_id=machine_id).order_by("-received_at")[:N]
    points = list(qs)
    itype = Incident.Type.MEM_HIGH
    active = _get_or_none_active_incident(machine_id, itype)

    if len(points) < N:
        if active:
            _resolve_incident(active)
        return

    if all(p.mem_percent > 90.0 for p in points):
        if not active:
            _open_incident(machine_id, itype, {"window_min": MEM_WINDOW_MIN, "samples": N})
        else:
            _touch_incident(active)
    else:
        if active:
            _resolve_incident(active)


def _check_disk_rule(machine_id):
    N = _disk_required_samples()
    qs = Metric.objects.filter(machine_id=machine_id).order_by("-received_at")[:N]
    points = list(qs)
    itype = Incident.Type.DISK_HIGH
    active = _get_or_none_active_incident(machine_id, itype)

    if len(points) < N:
        if active:
            _resolve_incident(active)
        return

    if all(p.disk_percent > 95.0 for p in points):
        if not active:
            _open_incident(machine_id, itype, {"window_min": DISK_WINDOW_MIN, "samples": N})
        else:
            _touch_incident(active)
    else:
        if active:
            _resolve_incident(active)


@shared_task
def evaluate_incidents_all():
    """
    Запускается каждые 5 минут.
    Проверяет все машины и применяет правила инцидентов.
    """
    ids = list(Machine.objects.filter(active=True).values_list("id", flat=True))
    logger.info("evaluate_incidents_all: %s machines", len(ids))
    for mid in ids:
        _check_cpu_rule(mid)
        _check_mem_rule(mid)
        _check_disk_rule(mid)
