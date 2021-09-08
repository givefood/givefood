from django.conf.urls import include, url
from views import *

urlpatterns = (
    url(r'^$', index, name="index"),
    url(r'^docs/$', docs, name="docs"),
    url(r'^foodbanks/$', foodbanks, name="foodbanks"),
    url(r'^foodbank/(?P<slug>[-\w]+)/$', foodbank, name="foodbank"),
    url(r'^foodbanks/search/$', foodbank_search, name="foodbank_search"),
    url(r'^locations/$', locations, name="locations"),
    url(r'^locations/search/$', location_search, name="location_search"),
    url(r'^needs/$', needs, name="needs"),
    url(r'^need/(?P<id>\b[0-9a-f]{8}\b)/$', need, name="need"),
    url(r'^constituencies/$', constituencies, name="constituencies"),
    url(r'^constituency/(?P<slug>[-\w]+)/$', constituency, name="constituency"),
)