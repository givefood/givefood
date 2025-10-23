from django.urls import path

from gfdumps import views

app_name = "dumps"

urlpatterns = [
    path("", views.dump_index, name="dump_index"),
    path("<str:dump_type>/", views.dump_type, name="dump_type"),
    path("<str:dump_type>/<str:dump_format>/", views.dump_format, name="dump_format"),
    path("<str:dump_type>/<str:dump_format>/latest/", views.dump_latest, name="dump_latest"),
    path("<str:dump_type>/<str:dump_format>/<int:year>-<int:month>-<int:day>/", views.dump_serve, name="dump_serve"),
]
