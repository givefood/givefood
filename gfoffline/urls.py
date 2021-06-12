from django.conf.urls import include, url
from views import *

urlpatterns = (
    url(r'^precacher/$', offline_precacher, name="offline_precacher"),
    url(r'^search/cleanup/$', offline_search_cleanup, name="offline_search_cleanup"),
    url(r'^search/saver/$', offline_search_saver, name="offline_search_saver"),
    url(r'^search/hydrate/$', offline_fire_search_hydrate, name="offline_fire_search_hydrate"),
)