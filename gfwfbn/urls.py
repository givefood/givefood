from django.views.generic import RedirectView
from gfwfbn.views import *
from django.urls import path, re_path

app_name = 'gfwfbn'

urlpatterns = [
    path("tt-old-data/", RedirectView.as_view(url='/dashboard/trusselltrust/old-data/')),

    path("", index, name="index"),
    path("rss.xml", rss, name="rss"),
    path("getlocation/", get_location, name="get_location"),
    path("geo.json", geojson, name="geojson"),
    path("manifest.json", manifest, name="manifest"),

    # Foodbank
    path("at/<slug:slug>/", foodbank, name="foodbank"),
    path("at/<slug:slug>/rss.xml", foodbank_rss, name="foodbank_rss"),
    path("at/<slug:slug>/geo.json", geojson, name="foodbank_geojson"),
    path("at/<slug:slug>/map.png", foodbank_map, name="foodbank_map"),
    path("at/<slug:slug>/news/", foodbank_news, name="foodbank_news"),
    path("at/<slug:slug>/socialmedia/", foodbank_socialmedia, name="foodbank_socialmedia"),
    path("at/<slug:slug>/nearby/", foodbank_nearby, name="foodbank_nearby"),
    path("at/<slug:slug>/history/", foodbank_history, name="foodbank_history"),
    path("at/<slug:slug>/subscribe/", foodbank_subscribe, name="foodbank_subscribe"),
    path("at/<slug:slug>/subscribe/sample/", foodbank_subscribe_sample, name="foodbank_subscribe_sample"),
    re_path(r"^at/(?P<slug>[-\w]+)/updates/(?P<action>subscribe|confirm|unsubscribe)/", updates, name="updates"),
    path("at/<slug:slug>/hit/", foodbank_hit, name="foodbank_hit"),

    # Edit
    path("at/<slug:slug>/edit/", foodbank_edit, name="foodbank_edit"),
    re_path(r"^at/(?P<slug>[-\w]+)/edit/(?P<action>needs|locations|contacts|donationpoints|closed)/", foodbank_edit_form, name="foodbank_edit_form"),
    re_path(r"^at/(?P<slug>[-\w]+)/edit/(?P<action>needs|locations|contacts|donationpoints|closed)/(?P<locslug>[-\w]+)/", foodbank_edit_form, name="foodbank_edit_form_location"),
    path("at/<slug:slug>/edit/thanks/", foodbank_edit_thanks, name="foodbank_edit_thanks"),

    # Donation Points
    path("at/<slug:slug>/donationpoints/", foodbank_donationpoints, name="foodbank_donationpoints"),
    path("at/<slug:slug>/donationpoint/<slug:dpslug>/", foodbank_donationpoint, name="foodbank_donationpoint"),
    path("at/<slug:slug>/donationpoint/<slug:dpslug>/photo/", foodbank_donationpoint_photo, name="foodbank_donationpoint_photo"),
    
    # Locations
    path("at/<slug:slug>/locations/", foodbank_locations, name="foodbank_locations"),
    path("at/<slug:slug>/<slug:locslug>/", foodbank_location, name="foodbank_location"),
    path("at/<slug:slug>/<slug:locslug>/map.png", foodbank_location_map, name="foodbank_location_map"),
    path("at/<slug:slug>/<slug:locslug>/photo/", foodbank_location_photo, name="foodbank_location_photo"),

    # Constituencies 
    path("in/constituencies/", constituencies, name="constituencies"),
    path("in/constituency/", RedirectView.as_view(url="/in/constituencies/")),
    path("in/constituency/<slug:slug>/", constituency, name="constituency"),
    path("in/constituency/<slug:parlcon_slug>/geo.json", geojson, name="constituency_geojson"),
]