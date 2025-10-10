import asyncio
import aiohttp
from celery import shared_task
from .models import Machine, Metric

@shared_task
def schedule_fetch_all():
    """Запускается Celery Beat по расписанию: опрашивает все активные машины."""
    machines = list(Machine.objects.filter(active=True))
    asyncio.run(fetch_all(machines))

async def fetch_all(machines):
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        tasks = [fetch_and_save(session, m.id, m.endpoint) for m in machines]
        await asyncio.gather(*tasks, return_exceptions=True)

async def fetch_and_save(session, machine_id, url):
    """GET -> JSON: {"cpu":60, "mem":"30%", "disk":"43%", "uptime":"1d 2h 37m 6s"}"""
    try:
        async with session.get(url) as resp:
            if resp.status != 200:
                return
            data = await resp.json()
            cpu = int(data.get("cpu"))
            mem = float(str(data.get("mem")).strip().rstrip("%"))
            disk = float(str(data.get("disk")).strip().rstrip("%"))
            uptime = str(data.get("uptime"))
            Metric.objects.create(
                machine_id=machine_id,
                cpu=cpu,
                mem_percent=mem,
                disk_percent=disk,
                uptime=uptime,
            )
    except Exception:
        # тут можно добавить логирование/метрики ошибок
        return
