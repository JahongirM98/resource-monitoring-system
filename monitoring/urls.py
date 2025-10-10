from django.urls import path
from . import views

urlpatterns = [
    path("login", views.login_view, name="login"),
    path("logout", views.logout_view, name="logout"),
    path("incidents", views.incidents_page, name="incidents"),
    path("api/incidents/json", views.incidents_json, name="incidents_json"),
]