from django.contrib import admin
from .models import Machine, Metric

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
