import os
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone

from .models import Incident

def incidents_page(request):
    return render(request, "monitoring/incidents.html")

def incidents_json(request):
    # Сначала активные, затем закрытые (последние 24 часа для компактности)
    since = timezone.now() - timezone.timedelta(days=1)
    qs = Incident.objects.select_related("machine").filter(started_at__gte=since).order_by("-is_active", "-last_seen_at")
    data = [
        {
            "id": i.id,
            "machine": i.machine.name,
            "type": i.type,
            "is_active": i.is_active,
            "started_at": i.started_at.isoformat(),
            "last_seen_at": i.last_seen_at.isoformat(),
            "resolved_at": i.resolved_at.isoformat() if i.resolved_at else None,
        }
        for i in qs
    ]
    return JsonResponse({"items": data, "count": len(data)})

@csrf_exempt
@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.method == "GET":
        return render(request, "monitoring/login.html")

    # POST
    username = (request.POST.get("username") or "").strip()
    password = (request.POST.get("password") or "").strip()
    want = os.getenv("AUTH_USERNAME", "admin"), os.getenv("AUTH_PASSWORD", "admin123")

    if (username, password) == want:
        request.session["auth_user"] = username
        return redirect("/incidents")
    return render(request, "monitoring/login.html", {"error": "Неверные учётные данные"}, status=401)

def logout_view(request):
    request.session.flush()
    return redirect("/login")
