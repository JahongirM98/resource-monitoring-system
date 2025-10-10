import re
from django.shortcuts import redirect
from django.conf import settings

EXEMPT_URLS = [
    r"^/login/?$",
    r"^/logout/?$",
    r"^/static/.*$",
    r"^/admin/.*$",          # если нужно заходить в админку
    r"^/api/health/?$",      # пригодится для будущих проверок
]

class SimpleAuthMiddleware:
    """
    Простейшая сессионная авторизация поверх Django SessionMiddleware.
    - Если в сессии нет 'auth_user' → редирект на /login
    - Исключения: EXEMPT_URLS
    Логин/пароль сравниваются во view c переменными окружения:
      AUTH_USERNAME, AUTH_PASSWORD
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self._compiled = [re.compile(p) for p in EXEMPT_URLS]

    def __call__(self, request):
        path = request.path
        is_exempt = any(rx.match(path) for rx in self._compiled)

        if not is_exempt and not request.session.get("auth_user"):
            return redirect("/login")

        return self.get_response(request)
