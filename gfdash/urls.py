from django.urls import re_path
from django.views.generic import RedirectView
from gfdash.views import *

app_name = "gfdash"

urlpatterns = (
    re_path(r'^$', index, name="index"),
    re_path(r'^items-requested-weekly/$', weekly_itemcount, name="weekly_itemcount"),
    re_path(r'^items-requested-weekly/by-year/$', weekly_itemcount_year, name="weekly_itemcount_year"),
    re_path(r'^most-requested-items/$', most_requested_items, name="most_requested_items"),
    re_path(r'^most-excess-items/$', most_excess_items, name="most_excess_items"),
    re_path(r'^item-categories/$', item_categories, name="item_categories"),
    re_path(r'^item-groups/$', item_groups, name="item_groups"),
    re_path(r'^trusselltrust/old-data/$', tt_old_data, name="tt_old_data"),
    re_path(r'^trusselltrust/most-requested-items/$', most_requested_items, name="tt_most_requested_items"),
    re_path(r'^articles/$', articles, name="articles"),
    re_path(r'^beautybanks/$', beautybanks, name="beautybanks"),
    re_path(r'^excess/$', excess, name="excess"),
    re_path(r'^foodbanks-found/$', foodbanks_found, name="foodbanks_found"),
    re_path(r'^bean-pasta-index/$', bean_pasta_index, name="bean_pasta_index"),
    re_path(r'^deliveries/(count|items|weight|calories)/$', deliveries, name="deliveries"),
    re_path(r'^donationpoints/supermarkets/$', supermarkets, name="supermarkets"),
    re_path(r'^charity-income-expenditure/$', charity_income_expenditure, name="charity_income_expenditure"),
    re_path(r'^price-per/kg/$', price_per_kg, name="price_per_kg"),
    re_path(r'^price-per/calorie/$', price_per_calorie, name="price_per_calorie"),
    re_path(r'^price-per-kg/$', RedirectView.as_view(url='/dashboard/price-per/kg/', permanent=True)),

)