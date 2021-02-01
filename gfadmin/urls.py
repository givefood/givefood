from django.conf.urls import include, url
from views import *

urlpatterns = (

    url(r'^$', index, name="admin_index"),

    url(r'^order/new/$', order_form, name="admin_neworder"),
    url(r'^order/(?P<id>[-\w]+)/$', order, name="admin_order"),
    url(r'^order/(?P<id>[-\w]+)/edit/$', order_form, name="admin_order_edit"),
    url(r'^order/(?P<id>[-\w]+)/sendnotification/$', order_send_notification, name="admin_order_send_notification"),

    url(r'^foodbanks/$', foodbanks, name="admin_foodbanks"),
    url(r'^foodbanks/christmascards/$', foodbanks_christmascards, name="admin_foodbanks_christmascards"),
    url(r'^foodbanks/csv/$', foodbanks_csv, name="admin_foodbanks_csv"),

    url(r'^orders/$', orders, name="admin_orders"),
    url(r'^orders/csv/$', orders_csv, name="admin_orders_csv"),

    url(r'^needs/$', needs, name="admin_needs"),
    url(r'^needs/csv/$', needs_csv, name="admin_needs_csv"),

    url(r'^items/$', items, name="admin_items"),
    url(r'^item/new/$', item_form, name="admin_item_new"),
    url(r'^item/(?P<slug>[-\w]+)/edit/$', item_form, name="admin_item_form"),

    url(r'^foodbank/new/$', foodbank_form, name="admin_newfoodbank"),
    url(r'^foodbank/(?P<slug>[-\w]+)/$', foodbank, name="admin_foodbank"),
    url(r'^foodbank/(?P<slug>[-\w]+)/edit/$', foodbank_form, name="admin_foodbank_edit"),
    url(r'^foodbank/(?P<slug>[-\w]+)/location/new/$', fblocation_form, name="admin_fblocation_new"),
    url(r'^foodbank/(?P<slug>[-\w]+)/location/(?P<loc_slug>[-\w]+)/edit/$', fblocation_form, name="admin_fblocation_edit"),
    url(r'^foodbank/(?P<slug>[-\w]+)/location/(?P<loc_slug>[-\w]+)/delete/$', fblocation_delete, name="admin_fblocation_delete"),
    url(r'^foodbank/(?P<slug>[-\w]+)/location/(?P<loc_slug>[-\w]+)/politics/edit/$', fblocation_politics_edit, name="admin_fblocation_politics_edit"),
    url(r'^foodbank/(?P<slug>[-\w]+)/politics/edit/$', foodbank_politics_form, name="admin_foodbank_politics_edit"),

    url(r'^need/new/$', need_form, name="admin_newneed"),
    url(r'^need/(?P<id>\b[0-9a-f]{8}\b)/$', need, name="admin_need"),
    url(r'^need/(?P<id>\b[0-9a-f]{8}\b)/edit/$', need_form, name="admin_need_form"),
    url(r'^need/(?P<id>\b[0-9a-f]{8}\b)/delete/$', need_delete, name="admin_need_delete"),
    url(r'^need/(?P<id>\b[0-9a-f]{8}\b)/publish/$', need_publish, name="admin_need_publish"),
    url(r'^need/(?P<id>\b[0-9a-f]{8}\b)/socialmedia/$', need_social_post, name="admin_need_social_post"),

    url(r'^locations/$', locations, name="admin_locations"),
    url(r'^locations/loader/sa/$', locations_loader_sa, name="admin_locations_loader_sa"),

    url(r'^parlcon/new/$', parlcon_form, name="admin_parlcon_form"),
    url(r'^parlcon/loader/$', parlcon_loader, name="admin_parlcon_loader"),
    url(r'^parlcon/loader/geojson/$', parlcon_loader_geojson, name="admin_parlcon_loader_geojson"),
    url(r'^parlcon/(?P<slug>[-\w]+)/edit/$', parlcon_form, name="admin_parlcon_form"),

    url(r'^politics/$', politics, name="admin_politics"),
    url(r'^politics/csv/$', politics_csv, name="admin_politics_csv"),

    url(r'^settings/$', settings, name="admin_settings"),
    url(r'^credentials/$', credentials, name="admin_credentials"),
    url(r'^credentials/new/$', credentials_form, name="admin_credential_new"),
    url(r'^searches/$', searches, name="admin_searches"),
    url(r'^searches/csv/$', searches_csv, name="admin_searches_csv"),
    url(r'^map/$', map, name="admin_map"),
    url(r'^search/$', search, name="admin_search"),
    url(r'^stats/$', stats, name="admin_stats"),

    url(r'^test_order_email/(?P<id>[-\w]+)/$', test_order_email, name="admin_test_order_email"),
    url(r'^resaver/orders/$', resave_orders, name="admin_resave_orders"),
)
