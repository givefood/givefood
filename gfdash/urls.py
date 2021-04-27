from django.conf.urls import include, url
from views import *

urlpatterns = (
    url(r'^$', dash_index, name="dash_index"),
    url(r'^items-requested-weekly/$', dash_weekly_itemcount, name="dash_weekly_itemcount"),
    url(r'^most-requested-items/$', dash_most_requested_items, name="dash_most_requested_items"),
    url(r'^trusselltrust/old-data/$', dash_tt_old_data, name="dash_tt_old_data"),
    url(r'^trusselltrust/most-requested-items/$', dash_most_requested_items, name="dash_tt_most_requested_items"),
)