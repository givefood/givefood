from gfwfbn.views import *
from django.urls import path, re_path

app_name = 'gfwfbn'

urlpatterns = [
    path("at/<slug:slug>/photo.jpg", foodbank_photo, name="foodbank_photo"),
    re_path(r"at/(?P<slug>[-\w]+)/screenshots/(?P<page_name>homepage|shoppinglist|donationpoints|contacts|locations).png", foodbank_screenshot, name="foodbank_screenshot"),
    path("at/<slug:slug>/hit/", foodbank_hit, name="foodbank_hit"),
    path("at/<slug:slug>/donationpoint/<slug:dpslug>/photo.jpg", foodbank_donationpoint_photo, name="foodbank_donationpoint_photo"),
    path("at/<slug:slug>/<slug:locslug>/photo.jpg", foodbank_location_photo, name="foodbank_location_photo"),
    
    # Web push notifications
    path("notifications/config/", notifications_config, name="notifications_config"),
    path("notifications/subscribe/", notifications_subscribe, name="notifications_subscribe"),
    path("notifications/unsubscribe/", notifications_unsubscribe, name="notifications_unsubscribe"),
]