from django.urls import path, re_path
from gfapi2.views import *

app_name = "gfapi2"

urlpatterns = (
    re_path(r'^$', index, name="index"),
    re_path(r'^docs/$', docs, name="docs"),
    re_path(r'^foodbanks/$', foodbanks, name="foodbanks"),
    re_path(r'^foodbank/(?P<slug>[-\w]+)/$', foodbank, name="foodbank"),
    re_path(r'^foodbanks/search/$', foodbank_search, name="foodbank_search"),
    re_path(r'^locations/$', locations, name="locations"),
    re_path(r'^locations/search/$', location_search, name="location_search"),
    re_path(r'^donationpoints/$', donationpoints, name="donationpoints"),
    re_path(r'^needs/$', needs, name="needs"),
    path("need/<uuid:id>/", need, name="need"),
    re_path(r'^constituencies/$', constituencies, name="constituencies"),
    re_path(r'^constituency/(?P<slug>[-\w]+)/$', constituency, name="constituency"),
)