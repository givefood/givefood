from django.urls import path
from gfapi1.views import *
from givefood.views import api

urlpatterns = (

    path("", api, name="api_index"),
    path("foodbanks/", api_foodbanks, name="api_foodbanks"),
    path("foodbanks/search/", api_foodbank_search, name="api_foodbank_search"),
    path("foodbank/<slug:slug>/", api_foodbank, name="api_foodbank"),
    path("needs/", api_needs, name="api_needs"),
    path("need/<uuid:id>/", api_need, name="api_need"),

)