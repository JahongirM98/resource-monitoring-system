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

class Incident(models.Model):
    class Type(models.TextChoices):
        CPU_HIGH = "CPU_HIGH", "CPU > 85%"
        MEM_HIGH = "MEM_HIGH", "MEM > 90% (30m)"
        DISK_HIGH = "DISK_HIGH", "DISK > 95% (2h)"

    machine = models.ForeignKey("Machine", on_delete=models.CASCADE, related_name="incidents")
    type = models.CharField(max_length=32, choices=Type.choices)
    is_active = models.BooleanField(default=True)

    started_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    details = models.JSONField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["machine", "type", "is_active"]),
            models.Index(fields=["started_at"]),
        ]

    def __str__(self):
        state = "ACTIVE" if self.is_active else "RESOLVED"
        return f"{self.machine.name} {self.type} [{state}]"