from django.conf.urls import include, url
from django.views.generic import RedirectView
from views import *

urlpatterns = (
    url(r'^tt-old-data/$', public_tt_old_data, name="public_tt_old_data"),
    url(r'^$', public_what_food_banks_need, name="public_what_food_banks_need"),
    url(r'^click/(?P<slug>[-\w]+)/$', public_what_food_banks_need_click, name="public_what_food_banks_need_click"),

    url(r'^at/(?P<slug>[-\w]+)/$', public_wfbn_foodbank, name="public_wfbn_foodbank"),
    url(r'^at/(?P<slug>[-\w]+)/map.png$', public_wfbn_foodbank_map, name="public_wfbn_foodbank_map"),
    url(r'^at/(?P<slug>[-\w]+)/(?P<locslug>[-\w]+)/$', public_wfbn_foodbank_location, name="public_wfbn_foodbank_location"),
    url(r'^at/(?P<slug>[-\w]+)/(?P<locslug>[-\w]+)/map.png$', public_wfbn_foodbank_location_map, name="public_wfbn_foodbank_location_map"),

    url(r'^in/constituencies/$', public_wfbn_constituencies, name="public_wfbn_constituencies"),
    url(r'^in/constituency/$', RedirectView.as_view(url="/in/constituencies/")),
    url(r'^in/constituency/(?P<slug>[-\w]+)/$', public_wfbn_constituency, name="public_wfbn_constituency"),
    url(r'^in/constituency/(?P<slug>[-\w]+)/mp_photo_(?P<size>full|threefour).png$', public_wfbn_constituency_mp_photo, name="public_wfbn_constituency_mp_photo"),
)