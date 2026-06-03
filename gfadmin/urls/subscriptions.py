from django.urls import path
from gfadmin.views import *

urlpatterns = [

    path("subscriptions/", subscriptions, name="subscriptions"),
    path("subscription/delete/", delete_subscription, name="delete_subscription"),

]
