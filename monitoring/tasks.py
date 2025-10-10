# monitoring/tasks.py
import asyncio
import aiohttp
import logging
from celery import shared_task
from asgiref.sync import sync_to_async
from datetime import timedelta
from django.utils import timezone
from .models import Machine, Metric, Incident

logger = logging.getLogger(__name__)

SAMPLE_INTERVAL_MIN = 15  # текущий период опроса метрик (минуты)
MEM_WINDOW_MIN = 30
DISK_WINDOW_MIN = 120

logger = logging.getLogger(__name__)

# Обёртки для ORM (выполняются в отдельном потоке из async-кода)
@sync_to_async
def _get_active_machines():
    return list(Machine.objects.filter(active=True).only("id", "endpoint"))

@sync_to_async
def _save_metric(machine_id, cpu, mem, disk, uptime):
    Metric.objects.create(
        machine_id=machine_id,
        cpu=cpu,
        mem_percent=mem,
        disk_percent=disk,
        uptime=uptime,
    )

@shared_task
def schedule_fetch_all():
    """
    Вызывается Celery Beat. Создаём event loop и гоняем асинхронные HTTP-запросы.
    Все обращения к ORM — через sync_to_async.
    """
    asyncio.run(_run())

async def _run():
    machines = await _get_active_machines()
    logger.info("schedule_fetch_all: %s machines", len(machines))

    timeout = aiohttp.ClientTimeout(total=10)
    connector = aiohttp.TCPConnector(limit=30)  # ограничим одновременный коннект
    async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
        tasks = [fetch_and_save(session, m.id, m.endpoint) for m in machines]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # опционально: логируем ошибки
        for r in results:
            if isinstance(r, Exception):
                logger.exception("fetch task error: %s", r)

async def fetch_and_save(session, machine_id, url: str):
    try:
        async with session.get(url) as resp:
            if resp.status != 200:
                logger.warning("non-200 from %s: %s", url, resp.status)
                return
            data = await resp.json()

            # парсим поля
            cpu = int(data["cpu"])
            mem = float(str(data["mem"]).rstrip("%"))
            disk = float(str(data["disk"]).rstrip("%"))
            uptime = str(data["uptime"])

            # сохраняем через sync_to_async
            await _save_metric(machine_id, cpu, mem, disk, uptime)
            # logger.info("saved from %s", url)
    except Exception as e:
        logger.exception("fetch error for %s: %s", url, e)

def _get_or_none_active_incident(machine_id, itype):
    return Incident.objects.filter(machine_id=machine_id, type=itype, is_active=True).first()

def _open_incident(machine_id, itype, details=None):
    Incident.objects.create(machine_id=machine_id, type=itype, is_active=True, details=details or {})
    logger.info("Incident OPEN: %s on machine %s", itype, machine_id)

def _touch_incident(incident: Incident):
    # last_seen_at обновится авто; просто сохраним
    incident.save(update_fields=["last_seen_at"])

def _resolve_incident(incident: Incident):
    if incident and incident.is_active:
        incident.is_active = False
        incident.resolved_at = timezone.now()
        incident.save(update_fields=["is_active", "resolved_at"])
        logger.info("Incident RESOLVED: %s on machine %s", incident.type, incident.machine_id)

def _mem_required_samples():
    # сколько точек нужно, чтобы покрыть окно 30 минут
    return max(2, MEM_WINDOW_MIN // SAMPLE_INTERVAL_MIN)

def _disk_required_samples():
    # 2 часа / 15 мин = 8
    return max(2, DISK_WINDOW_MIN // SAMPLE_INTERVAL_MIN)

def _check_cpu_rule(machine_id):
    # «на любом замере» > 85 -> инцидент
    latest = Metric.objects.filter(machine_id=machine_id).order_by("-received_at").first()
    itype = Incident.Type.CPU_HIGH
    active = _get_or_none_active_incident(machine_id, itype)

    if latest and latest.cpu > 85:
        # триггер
        if not active:
            _open_incident(machine_id, itype, {"cpu": latest.cpu, "at": latest.received_at.isoformat()})
        else:
            _touch_incident(active)
    else:
        # нормализовалось — закрываем активный
        if active:
            _resolve_incident(active)

def _check_mem_rule(machine_id):
    # «>90% в течение 30 минут» -> все последние N точек (окно) должны быть >90
    N = _mem_required_samples()
    qs = Metric.objects.filter(machine_id=machine_id).order_by("-received_at")[:N]
    points = list(qs)
    itype = Incident.Type.MEM_HIGH
    active = _get_or_none_active_incident(machine_id, itype)

    if len(points) < N:
        # данных недостаточно — считаем нормой, закрываем если было
        if active:
            _resolve_incident(active)
        return

    if all(p.mem_percent > 90.0 for p in points):
        # окно превышено
        if not active:
            _open_incident(machine_id, itype, {"window_min": MEM_WINDOW_MIN, "samples": N})
        else:
            _touch_incident(active)
    else:
        if active:
            _resolve_incident(active)

def _check_disk_rule(machine_id):
    # «>95% в течение 2 часов» -> все последние N точек >95
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
    """Запускай каждые 5 минут. Обходит все машины и применяет правила."""
    ids = list(Machine.objects.filter(active=True).values_list("id", flat=True))
    logger.info("evaluate_incidents_all: %s machines", len(ids))
    for mid in ids:
        _check_cpu_rule(mid)
        _check_mem_rule(mid)
        _check_disk_rule(mid)