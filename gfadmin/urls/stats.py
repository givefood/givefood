from django.urls import path
from gfadmin.views import *

urlpatterns = [

    path("stats/quarter/", quarter_stats, name="quarter_stats"),
    path("stats/orders/", order_stats, name="order_stats"),
    path("stats/editing/", edit_stats, name="edit_stats"),
    path("stats/subscribers/", subscriber_stats, name="subscriber_stats"),
    path("stats/subscribers/graph/", subscriber_graph, name="subscriber_graph"),
    path("stats/needs/", need_stats, name="need_stats"),

]
