from django.urls import path
from gfapp.views import *

app_name = "gfapp"

urlpatterns = [
    path("", index, name="index"),
    path("map/", map, name="map"),
    path("fb/<slug:slug>/", foodbank, name="foodbank"),
    path("search/", search_results, name="search_results"),
]