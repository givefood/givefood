from django.urls import path, re_path
from django.views.generic import RedirectView
from gfdash.views import *

app_name = "gfdash"

urlpatterns = (
    path("", index, name="index"),
    path("items-requested-weekly/", weekly_itemcount, name="weekly_itemcount"),
    path("items-requested-weekly/by-year/", weekly_itemcount_year, name="weekly_itemcount_year"),
    path("most-requested-items/", most_requested_items, name="most_requested_items"),
    path("most-excess-items/", most_excess_items, name="most_excess_items"),
    path("item-categories/", item_categories, name="item_categories"),
    path("item-groups/", item_groups, name="item_groups"),
    path("trusselltrust/old-data/", tt_old_data, name="tt_old_data"),
    path("trusselltrust/most-requested-items/", most_requested_items, name="tt_most_requested_items"),
    path("articles/", articles, name="articles"),
    path("beautybanks/", beautybanks, name="beautybanks"),
    path("excess/", excess, name="excess"),
    path("foodbanks-found/", foodbanks_found, name="foodbanks_found"),
    path("bean-pasta-index/", bean_pasta_index, name="bean_pasta_index"),
    re_path(r'^deliveries/(count|items|weight|calories)/$', deliveries, name="deliveries"),
    path("donationpoints/supermarkets/", supermarkets, name="supermarkets"),
    path("charity-income-expenditure/", charity_income_expenditure, name="charity_income_expenditure"),
    path("price-per/kg/", price_per_kg, name="price_per_kg"),
    path("price-per/calorie/", price_per_calorie, name="price_per_calorie"),
    path("price-per-kg/", RedirectView.as_view(url='/dashboard/price-per/kg/', permanent=True)),

)