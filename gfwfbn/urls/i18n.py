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
    path("at/<slug:slug>/news/", foodbank_news, name="foodbank_news"),
    path("at/<slug:slug>/charity/", foodbank_charity, name="foodbank_charity"),
    path("at/<slug:slug>/socialmedia/", foodbank_socialmedia, name="foodbank_socialmedia"),
    path("at/<slug:slug>/nearby/", foodbank_nearby, name="foodbank_nearby"),
    path("at/<slug:slug>/subscribe/", foodbank_subscribe, name="foodbank_subscribe"),
    path("at/<slug:slug>/subscribe/sample/", foodbank_subscribe_sample, name="foodbank_subscribe_sample"),
    re_path(r"^at/(?P<slug>[-\w]+)/updates/(?P<action>subscribe|confirm|unsubscribe)/", updates, name="updates"),
    path("at/<slug:slug>/map.png", foodbank_map, name="foodbank_map"),
    path("at/<slug:slug>/maps/<int:size>.png", foodbank_map, name="foodbank_map_size"),

    # Donation Points
    path("at/<slug:slug>/donationpoints/", foodbank_donationpoints, name="foodbank_donationpoints"),
    path("at/<slug:slug>/donationpoint/<slug:dpslug>/", foodbank_donationpoint, name="foodbank_donationpoint"),
    path("at/<slug:slug>/donationpoint/<slug:dpslug>/openinghours/", foodbank_donationpoint_openinghours, name="foodbank_donationpoint_openinghours"),
    
    # Locations
    path("at/<slug:slug>/locations/", foodbank_locations, name="foodbank_locations"),
    path("at/<slug:slug>/<slug:locslug>/geo.json", geojson, name="foodbank_location_geojson"),
    path("at/<slug:slug>/<slug:locslug>/map.png", foodbank_location_map, name="foodbank_location_map"),
    path("at/<slug:slug>/<slug:locslug>/maps/<int:size>.png", foodbank_location_map, name="foodbank_location_map_size"),
    path("at/<slug:slug>/<slug:locslug>/", foodbank_location, name="foodbank_location"),

    # Constituencies 
    path("in/constituencies/", constituencies, name="constituencies"),
    path("in/constituency/", RedirectView.as_view(url="/in/constituencies/")),
    path("in/constituency/<slug:slug>/", constituency, name="constituency"),
    path("in/constituency/<slug:parlcon_slug>/geo.json", geojson, name="constituency_geojson"),
]