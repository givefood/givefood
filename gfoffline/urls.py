from django.conf.urls import include, url
from gfoffline.views import *

app_name = "gfoffline"

urlpatterns = (
    url(r'^precacher/$', precacher, name="precacher"),
    url(r'^oc_geocode/$', fire_oc_geocode, name="fire_oc_geocode"),
    url(r'^crawl_articles/$', crawl_articles, name="crawl_articles"),
    url(r'^cleanup_subs/$', cleanup_subs, name="cleanup_subs"),
    url(r'^days_between_needs/$', days_between_needs, name="days_between_needs"),
    url(r'^resaver/$', resaver, name="resaver"),
    url(r'^pluscodes/$', pluscodes, name="pluscodes"),
    url(r'^place_ids/$', place_ids, name="place_ids"),
)