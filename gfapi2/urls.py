from django.urls import path
from gfapi2.views import *

app_name = "gfapi2"

urlpatterns = (
    path("", index, name="index"),
    path("docs/", docs, name="docs"),
    path("foodbanks/", foodbanks, name="foodbanks"),
    path("foodbank/<slug:slug>/", foodbank, name="foodbank"),
    path("foodbanks/search/", foodbank_search, name="foodbank_search"),
    path("locations/", locations, name="locations"),
    path("locations/search/", location_search, name="location_search"),
    path("donationpoints/", donationpoints, name="donationpoints"),
    path("needs/", needs, name="needs"),
    path("need/<uuid:id>/", need, name="need"),
    path("constituencies/", constituencies, name="constituencies"),
    path("constituency/<slug:slug>/", constituency, name="constituency"),
)