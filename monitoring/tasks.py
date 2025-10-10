# monitoring/tasks.py
import asyncio
import aiohttp
import logging
from celery import shared_task
from asgiref.sync import sync_to_async

from .models import Machine, Metric

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
