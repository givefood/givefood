from django.conf.urls import include, url
from gfdash.views import *

app_name = "gfdash"

urlpatterns = (
    url(r'^$', index, name="index"),
    url(r'^items-requested-weekly/$', weekly_itemcount, name="weekly_itemcount"),
    url(r'^most-requested-items/$', most_requested_items, name="most_requested_items"),
    url(r'^trusselltrust/old-data/$', tt_old_data, name="tt_old_data"),
    url(r'^trusselltrust/most-requested-items/$', most_requested_items, name="tt_most_requested_items"),
    url(r'^articles/$', articles, name="articles"),
    url(r'^beautybanks/$', beautybanks, name="beautybanks"),
    url(r'^excess/$', excess, name="excess"),

)