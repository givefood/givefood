from gfwfbn.views import *
from django.urls import path

app_name = 'gfwfbn'

urlpatterns = [
    path("at/<slug:slug>/", md_foodbank, name="md_foodbank"),
    path("at/<slug:slug>/locations/", md_foodbank_locations, name="md_foodbank_locations"),
    path("at/<slug:slug>/donationpoints/", md_foodbank_donationpoints, name="md_foodbank_donationpoints"),
    path("at/<slug:slug>/donationpoint/<slug:dpslug>/", md_foodbank_donationpoint, name="md_foodbank_donationpoint"),
    path("at/<slug:slug>/news/", md_foodbank_news, name="md_foodbank_news"),
    path("at/<slug:slug>/charity/", md_foodbank_charity, name="md_foodbank_charity"),
    path("at/<slug:slug>/nearby/", md_foodbank_nearby, name="md_foodbank_nearby"),
    path("at/<slug:slug>/<slug:locslug>/", md_foodbank_location, name="md_foodbank_location"),
]
