from django.urls import path
from gfadmin.views import *

urlpatterns = [

    path("items/", items, name="items"),
    path("item/new/", item_form, name="item_new"),
    path("item/<slug:slug>/edit/", item_form, name="item_form"),

]
