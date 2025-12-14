from gfwfbn.views import *
from django.urls import path, re_path

app_name = 'gfwfbn'

urlpatterns = [

    # Hits
    path("at/<slug:slug>/hit/", foodbank_hit, name="foodbank_hit"),

    # Photos and screenshots
    path("at/<slug:slug>/photo.jpg", foodbank_photo, name="foodbank_photo"),
    re_path(r"at/(?P<slug>[-\w]+)/screenshots/(?P<page_name>homepage|shoppinglist|donationpoints|contacts|locations).png", foodbank_screenshot, name="foodbank_screenshot"),
    path("at/<slug:slug>/donationpoint/<slug:dpslug>/photo.jpg", foodbank_donationpoint_photo, name="foodbank_donationpoint_photo"),
    path("at/<slug:slug>/<slug:locslug>/photo.jpg", foodbank_location_photo, name="foodbank_location_photo"),
    
    # Web push notifications
    path("webpush/config/", webpush_config, name="webpush_config"),
    path("webpush/subscribe/<slug:slug>/", webpush_subscribe, name="webpush_subscribe"),
    path("webpush/unsubscribe/<slug:slug>/", webpush_unsubscribe, name="webpush_unsubscribe"),

    # Mobile sub hits
    path("mobsub/", mobsub, name="mobsub"),

]