from django.conf.urls import include, url
from views import *

urlpatterns = (

    url(r'^foodbanks/$', api_foodbanks, name="api_foodbanks"),
    url(r'^foodbanks/search/$', api_foodbank_search, name="api_foodbank_search"),
    url(r'^foodbank/(?P<slug>[-\w]+)/$', api_foodbank, name="api_foodbank"),
    url(r'^foodbank/$', api_foodbank_key, name="api_foodbank_key"),
    url(r'^needs/$', api_needs, name="api_needs"),
    url(r'^need/(?P<id>\b[0-9a-f]{8}\b)/$', api_need, name="api_need"),

)