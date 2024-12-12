from django.urls import path, re_path
from gfapi1.views import *
from givefood.views import api

urlpatterns = (

    re_path(r'^$', api, name="api_index"),
    re_path(r'^foodbanks/$', api_foodbanks, name="api_foodbanks"),
    re_path(r'^foodbanks/search/$', api_foodbank_search, name="api_foodbank_search"),
    re_path(r'^foodbank/(?P<slug>[-\w]+)/$', api_foodbank, name="api_foodbank"),
    re_path(r'^needs/$', api_needs, name="api_needs"),
    re_path(r'^need/(?P<id>\b[0-9a-f]{8}\b)/$', api_need, name="api_need"),

)