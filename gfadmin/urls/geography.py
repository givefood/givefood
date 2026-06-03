from django.urls import path
from gfadmin.views import *

urlpatterns = [

    path("locations/", locations, name="locations"),
    path("locations/loader/sa/", locations_loader_sa, name="locations_loader_sa"),

    path("parlcon/new/", parlcon_form, name="parlcon_form"),
    path("parlcon/loader/", parlcon_loader, name="parlcon_loader"),
    path("parlcon/loader/geojson/", parlcon_loader_geojson, name="parlcon_loader_geojson"),
    path("parlcon/loader/centre/", parlcon_loader_centre, name="parlcon_loader_centre"),
    path("parlcon/loader/twitter/", parlcon_loader_twitter_handle, name="parlcon_loader_twitter_handle"),
    path("parlcon/<slug:slug>/edit/", parlcon_form, name="parlcon_form"),

    path("places/", places, name="places"),
    path("places/loader/", places_loader, name="places_loader"),
    path("place/<int:pk>/edit/", place_form, name="place_form"),

    path("politics/", politics, name="politics"),
    path("politics/csv/", politics_csv, name="politics_csv"),

]
