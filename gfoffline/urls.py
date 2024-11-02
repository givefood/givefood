from django.conf.urls import include, url
from gfoffline.views import *

app_name = "gfoffline"

urlpatterns = (
    url(r'^precacher/$', precacher, name="precacher"),
    url(r'^oc_geocode/$', fire_oc_geocode, name="fire_oc_geocode"),
    url(r'^crawl_articles/$', crawl_articles, name="crawl_articles"),
    url(r'^discrepancy_check/$', discrepancy_check, name="discrepancy_check"),
    url(r'^need_check/$', need_check, name="need_check"),
    url(r'^foodbank_need_check/(?P<slug>[-\w]+)/$', foodbank_need_check, name="foodbank_need_check"),
    url(r'^decache_donationpoints/$', decache_donationpoints, name="decache_donationpoints"),
    url(r'^cleanup_subs/$', cleanup_subs, name="cleanup_subs"),
    url(r'^days_between_needs/$', days_between_needs, name="days_between_needs"),
    url(r'^resaver/$', resaver, name="resaver"),
    url(r'^pluscodes/$', pluscodes, name="pluscodes"),
    url(r'^place_ids/$', place_ids, name="place_ids"),
    url(r'^need_categorisation/$', need_categorisation, name="need_categorisation"),
    url(r'^load_mps/$', load_mps, name="load_mps"),
    url(r'^refresh_mps/$', refresh_mps, name="refresh_mps"),
)