from django.conf.urls import include, url
from django.views.generic import RedirectView
from views import *

urlpatterns = (
    url(r'^tt-old-data/$', RedirectView.as_view(url='/dashboard/trusselltrust/old-data/')),

    url(r'^$', public_what_food_banks_need, name="public_what_food_banks_need"),

    url(r'^updates/(?P<action>subscribe|confirm|unsubscribe)/$', public_what_food_banks_need_updates, name="public_what_food_banks_need_updates"),

    url(r'^at/(?P<slug>[-\w]+)/$', public_wfbn_foodbank, name="public_wfbn_foodbank"),
    url(r'^at/(?P<slug>[-\w]+)/map.png$', public_wfbn_foodbank_map, name="public_wfbn_foodbank_map"),
    url(r'^at/(?P<slug>[-\w]+)/history/$', public_wfbn_foodbank_history, name="public_wfbn_foodbank_history"),

    url(r'^at/(?P<slug>[-\w]+)/edit/$', public_wfbn_foodbank_edit, name="public_wfbn_foodbank_edit"),
    url(r'^at/(?P<slug>[-\w]+)/edit/(?P<action>needs|locations|contacts|closed)/$', public_wfbn_foodbank_edit_form, name="public_wfbn_foodbank_edit_form"),
    url(r'^at/(?P<slug>[-\w]+)/edit/(?P<action>needs|locations|contacts|closed)/(?P<locslug>[-\w]+)/$', public_wfbn_foodbank_edit_form, name="public_wfbn_foodbank_edit_form_location"),
    url(r'^at/(?P<slug>[-\w]+)/edit/thanks/$', public_wfbn_foodbank_edit_thanks, name="public_wfbn_foodbank_edit_thanks"),

    url(r'^at/(?P<slug>[-\w]+)/(?P<locslug>[-\w]+)/$', public_wfbn_foodbank_location, name="public_wfbn_foodbank_location"),
    url(r'^at/(?P<slug>[-\w]+)/(?P<locslug>[-\w]+)/map.png$', public_wfbn_foodbank_location_map, name="public_wfbn_foodbank_location_map"),

    url(r'^in/constituencies/$', public_wfbn_constituencies, name="public_wfbn_constituencies"),
    url(r'^in/constituency/$', RedirectView.as_view(url="/in/constituencies/")),
    url(r'^in/constituency/(?P<slug>[-\w]+)/$', public_wfbn_constituency, name="public_wfbn_constituency"),
    url(r'^in/constituency/(?P<slug>[-\w]+)/mp_photo_(?P<size>full|threefour).png$', public_wfbn_constituency_mp_photo, name="public_wfbn_constituency_mp_photo"),
)