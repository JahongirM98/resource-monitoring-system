from django.core.management.base import BaseCommand
from django.utils import timezone as tz
from datetime import timedelta as td
from monitoring.models import Machine, Metric
from monitoring.tasks import evaluate_incidents_all
import requests

class Command(BaseCommand):
    help = "Initial seeding: create demo machines and metrics"

    def handle(self, *args, **options):
        host = "http://mock:8001"
        self.stdout.write(self.style.MIGRATE_HEADING("Seeding demo data..."))

        # 1. Создание машин
        try:
            r = requests.get(f"{host}/m/list", timeout=5)
            if r.status_code == 200:
                data = r.json()
                Machine.objects.all().delete()
                for item in data:
                    Machine.objects.create(
                        name=item["name"],
                        endpoint=f"{host}/m/{item['id']}/metrics",
                    )
                self.stdout.write(self.style.SUCCESS(f"✅ Created {len(data)} machines"))
            else:
                self.stdout.write(self.style.WARNING("⚠️ Mock server not responding, skipping"))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"⚠️ Cannot reach mock server: {e}"))

        if not Machine.objects.exists():
            self.stdout.write(self.style.WARNING("⚠️ No machines found — aborting seed"))
            return

        # 2. Создание тестовых метрик
        now = tz.now()
        m1 = Machine.objects.filter(name='node-01').first()
        m2 = Machine.objects.filter(name='node-02').first()
        m3 = Machine.objects.filter(name='node-03').first()

        if m1:
            Metric.objects.create(machine=m1, cpu=96, mem_percent=20, disk_percent=20,
                                  uptime='cpu_spike', received_at=now)
        if m2:
            Metric.objects.create(machine=m2, cpu=10, mem_percent=95, disk_percent=20,
                                  uptime='mem1', received_at=now - td(minutes=15))
            Metric.objects.create(machine=m2, cpu=12, mem_percent=96, disk_percent=25,
                                  uptime='mem2', received_at=now)
        if m3:
            for i in range(8):
                Metric.objects.create(machine=m3, cpu=8, mem_percent=30, disk_percent=98,
                                      uptime=f'disk{i}', received_at=now - td(minutes=15*i))
        self.stdout.write(self.style.SUCCESS("✅ Demo metrics added"))

        # 3. Пересчёт инцидентов
        evaluate_incidents_all()
        self.stdout.write(self.style.SUCCESS("✅ Incidents evaluated"))
