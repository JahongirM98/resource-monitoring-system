from django.contrib import admin
from .models import Machine, Metric, Incident


@admin.register(Machine)
class MachineAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "endpoint", "active", "created_at")
    list_filter = ("active",)
    search_fields = ("name", "endpoint")

@admin.register(Metric)
class MetricAdmin(admin.ModelAdmin):
    list_display = ("id", "machine", "cpu", "mem_percent", "disk_percent", "uptime", "received_at")
    list_filter = ("machine",)
    search_fields = ("machine__name", "uptime")

@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display = ("id", "machine", "type", "is_active", "started_at", "last_seen_at", "resolved_at")
    list_filter = ("type", "is_active", "machine")
    search_fields = ("machine__name",)