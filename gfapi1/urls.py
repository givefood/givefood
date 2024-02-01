from django.conf.urls import url
from gfapi1.views import *
from givefood.views import api

urlpatterns = (

    url(r'^$', api, name="api_index"),
    url(r'^foodbanks/$', api_foodbanks, name="api_foodbanks"),
    url(r'^foodbanks/search/$', api_foodbank_search, name="api_foodbank_search"),
    url(r'^foodbank/(?P<slug>[-\w]+)/$', api_foodbank, name="api_foodbank"),
    url(r'^needs/$', api_needs, name="api_needs"),
    url(r'^need/(?P<id>\b[0-9a-f]{8}\b)/$', api_need, name="api_need"),

)