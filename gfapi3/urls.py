from django.urls import re_path
from gfapi3.views import *

app_name = "gfapi3"

urlpatterns = (
    re_path(r'^$', index, name="index"),
    re_path(r'^csv/$', everything_csv, name="everything_csv"),
)