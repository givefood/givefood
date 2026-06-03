from django.urls import path
from gfadmin.views import *

urlpatterns = [

    path("order/new/", order_form, name="neworder"),
    path("order/<slug:id>/", order, name="order"),
    path("order/<slug:id>/edit/", order_form, name="order_edit"),
    path("order/<slug:id>/sendnotification/", order_send_notification, name="order_send_notification"),
    path("order/<slug:id>/delete/", order_delete, name="order_delete"),
    path("order/<slug:id>/email/", order_email, name="order_email"),

    path("orders/", orders, name="orders"),
    path("orders/csv/", orders_csv, name="orders_csv"),

    path("order-groups/", order_groups, name="order_groups"),
    path("order-group/<slug:slug>/", order_group, name="order_group"),
    path("order-group/<slug:slug>/edit/", order_group_form, name="order_group_edit"),
    path("order-groups/new/", order_group_form, name="order_group_new"),

]
