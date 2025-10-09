from django.db import models

class Machine(models.Model):
    name = models.CharField(max_length=128)
    endpoint = models.URLField(help_text="HTTP URL вида http://host:port/metrics")
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({'on' if self.active else 'off'})"

class Metric(models.Model):
    machine = models.ForeignKey(Machine, on_delete=models.CASCADE, related_name="metrics")
    cpu = models.IntegerField()
    mem_percent = models.FloatField()
    disk_percent = models.FloatField()
    uptime = models.CharField(max_length=64)
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["machine", "received_at"])]
        ordering = ["-received_at"]
