from django.urls import path
from gfapp.views import *

app_name = "gfapp"

urlpatterns = [
    path("", index, name="index"),
    path("search/", search, name="search"),
    path("fb/<slug:slug>/", foodbank, name="foodbank"),
    path("fb/<slug:slug>/<slug:locslug>/", location, name="location"),
]