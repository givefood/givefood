from django.urls import path
from gfadmin.views import *

urlpatterns = [

    path("crawl-sets/", crawl_sets, name="crawl_sets"),
    path("crawl-set/<int:crawl_set_id>.json", crawl_set_json, name="crawl_set_json"),
    path("crawl-set/<int:crawl_set_id>/", crawl_set, name="crawl_set"),

]
