from django.conf.urls import url
from gfapi3.views import *

app_name = "gfapi3"

urlpatterns = (
    url(r'^$', index, name="index"),
    url(r'^csv/$', everything_csv, name="everything_csv"),
)