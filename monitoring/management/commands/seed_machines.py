from django.core.management.base import BaseCommand
from monitoring.models import Machine

class Command(BaseCommand):
    help = "Создаёт 30 машин с endpoint-ами мок-сервера"

    def add_arguments(self, parser):
        parser.add_argument(
            "--host",
            default="http://127.0.0.1:8001",
            help="Базовый хост мок-сервера, напр. http://127.0.0.1:8001",
        )

    def handle(self, *args, **opts):
        host = opts["host"].rstrip("/")
        created = 0
        for i in range(1, 31):
            name = f"node-{i:02d}"
            endpoint = f"{host}/m/{i}/metrics"
            _, is_created = Machine.objects.get_or_create(
                name=name, endpoint=endpoint, defaults={"active": True}
            )
            if is_created:
                created += 1
        self.stdout.write(self.style.SUCCESS(f"OK: создано {created} машин"))
