from django.urls import path
from gfapi3.views import *

app_name = "gfapi3"

urlpatterns = (
    path("", index, name="index"),
    path("donationpoints/company/<slug:slug>/", company, name="company"),
)