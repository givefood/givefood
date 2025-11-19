from django.urls import path
from gfadmin2 import views

app_name = "gfadmin2"

urlpatterns = [
    # Dashboard
    path("", views.index, name="index"),
    
    # Foodbanks
    path("foodbanks/", views.foodbanks_list, name="foodbanks_list"),
    path("foodbank/<slug:slug>/", views.foodbank_detail, name="foodbank_detail"),
    path("foodbank/<slug:slug>/edit/", views.foodbank_form, name="foodbank_edit"),
    path("foodbank/new/", views.foodbank_form, name="foodbank_new"),
    
    # Needs
    path("needs/", views.needs_list, name="needs_list"),
    path("need/<uuid:id>/", views.need_detail, name="need_detail"),
    path("need/<uuid:id>/publish/", views.need_publish, name="need_publish"),
    path("need/<uuid:id>/delete/", views.need_delete, name="need_delete"),
    
    # Orders
    path("orders/", views.orders_list, name="orders_list"),
    path("order/<slug:id>/", views.order_detail, name="order_detail"),
    
    # Search
    path("search/", views.search, name="search"),
]
