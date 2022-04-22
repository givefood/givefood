from django.conf.urls import include, url
from gfoffline.views import *

app_name = "gfoffline"

urlpatterns = (
    url(r'^precacher/$', precacher, name="precacher"),
    url(r'^oc_geocode/$', fire_oc_geocode, name="fire_oc_geocode"),
    url(r'^search/cleanup/$', search_cleanup, name="search_cleanup"),
    url(r'^search/saver/$', search_saver, name="search_saver"),
    url(r'^search/hydrate/$', fire_search_hydrate, name="fire_search_hydrate"),
    url(r'^crawl_articles/$', crawl_articles, name="crawl_articles"),
    url(r'^cleanup_subs/$', cleanup_subs, name="cleanup_subs"),
    url(r'^days_between_needs/$', days_between_needs, name="days_between_needs"),
)