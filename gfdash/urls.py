from django.conf.urls import include, url
from views import *

urlpatterns = (
    url(r'^$', dash_index, name="dash_index"),
    url(r'^trusselltrust/old-data/$', dash_tt_old_data, name="dash_tt_old_data"),
    url(r'^trusselltrust/most-requested-items/$', dash_tt_most_requested_items, name="dash_tt_most_requested_items"),
)