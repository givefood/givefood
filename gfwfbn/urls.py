from django.conf.urls import include, url
from django.views.generic import RedirectView
from gfwfbn.views import *

app_name = 'gfwfbn'

urlpatterns = (
    url(r'^tt-old-data/$', RedirectView.as_view(url='/dashboard/trusselltrust/old-data/')),

    url(r'^$', index, name="index"),
    url(r'^rss.xml$', rss, name="rss"),
    url(r'^trusselltrust/$', trussell_trust_index, name="trussell_trust_index"),
    url(r'^getlocation/$', get_location, name="get_location"),
    url(r'^click/(?P<slug>[-\w]+)/$', click, name="click"),
    url(r'^updates/(?P<action>subscribe|confirm|unsubscribe)/$', updates, name="updates"),

    # Foodbank
    url(r'^at/(?P<slug>[-\w]+)/$', foodbank, name="foodbank"),
    url(r'^at/(?P<slug>[-\w]+)/rss.xml$', foodbank_rss, name="foodbank_rss"),
    url(r'^at/(?P<slug>[-\w]+)/map.png$', foodbank_map, name="foodbank_map"),
    url(r'^at/(?P<slug>[-\w]+)/news/$', foodbank_news, name="foodbank_news"),
    url(r'^at/(?P<slug>[-\w]+)/socialmedia/$', foodbank_socialmedia, name="foodbank_socialmedia"),
    url(r'^at/(?P<slug>[-\w]+)/nearby/$', foodbank_nearby, name="foodbank_nearby"),
    url(r'^at/(?P<slug>[-\w]+)/history/$', foodbank_history, name="foodbank_history"),
    url(r'^at/(?P<slug>[-\w]+)/subscribe/$', foodbank_subscribe, name="foodbank_subscribe"),
    url(r'^at/(?P<slug>[-\w]+)/subscribe/sample/$', foodbank_subscribe_sample, name="foodbank_subscribe_sample"),
    url(r'^at/(?P<slug>[-\w]+)/updates/(?P<action>subscribe|confirm|unsubscribe)/$', updates, name="updates"),
    url(r'^at/(?P<slug>[-\w]+)/hit/$', foodbank_hit, name="foodbank_hit"),

    # Edit
    url(r'^at/(?P<slug>[-\w]+)/edit/$', foodbank_edit, name="foodbank_edit"),
    url(r'^at/(?P<slug>[-\w]+)/edit/(?P<action>needs|locations|contacts|closed)/$', foodbank_edit_form, name="foodbank_edit_form"),
    url(r'^at/(?P<slug>[-\w]+)/edit/(?P<action>needs|locations|contacts|closed)/(?P<locslug>[-\w]+)/$', foodbank_edit_form, name="foodbank_edit_form_location"),
    url(r'^at/(?P<slug>[-\w]+)/edit/thanks/$', foodbank_edit_thanks, name="foodbank_edit_thanks"),
    
    # Locations
    url(r'^at/(?P<slug>[-\w]+)/locations/$', foodbank_locations, name="foodbank_locations"),
    url(r'^at/(?P<slug>[-\w]+)/(?P<locslug>[-\w]+)/$', foodbank_location, name="foodbank_location"),
    url(r'^at/(?P<slug>[-\w]+)/(?P<locslug>[-\w]+)/map.png$', foodbank_location_map, name="foodbank_location_map"),

    # Constituencies 
    url(r'^in/constituencies/$', constituencies, name="constituencies"),
    url(r'^in/constituency/$', RedirectView.as_view(url="/in/constituencies/")),
    url(r'^in/constituency/(?P<slug>[-\w]+)/$', constituency, name="constituency"),
)