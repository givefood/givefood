from django.conf.urls import include, url
from gfadmin.views import *

app_name = "gfadmin"

urlpatterns = (

    url(r'^$', index, name="index"),

    url(r'^order/new/$', order_form, name="neworder"),
    url(r'^order/(?P<id>[-\w]+)/$', order, name="order"),
    url(r'^order/(?P<id>[-\w]+)/edit/$', order_form, name="order_edit"),
    url(r'^order/(?P<id>[-\w]+)/sendnotification/$', order_send_notification, name="order_send_notification"),
    url(r'^order/(?P<id>[-\w]+)/delete/$', order_delete, name="order_delete"),

    url(r'^foodbanks/$', foodbanks, name="foodbanks"),
    url(r'^foodbanks/christmascards/$', foodbanks_christmascards, name="foodbanks_christmascards"),
    url(r'^foodbanks/csv/$', foodbanks_csv, name="foodbanks_csv"),

    url(r'^orders/$', orders, name="orders"),
    url(r'^orders/csv/$', orders_csv, name="orders_csv"),

    url(r'^needs/$', needs, name="needs"),
    url(r'^needs/csv/$', needs_csv, name="needs_csv"),

    url(r'^items/$', items, name="items"),
    url(r'^item/new/$', item_form, name="item_new"),
    url(r'^item/(?P<slug>[-\w]+)/edit/$', item_form, name="item_form"),

    url(r'^foodbank/new/$', foodbank_form, name="newfoodbank"),
    url(r'^foodbank/(?P<slug>[-\w]+)/$', foodbank, name="foodbank"),
    url(r'^foodbank/(?P<slug>[-\w]+)/edit/$', foodbank_form, name="foodbank_edit"),
    url(r'^foodbank/(?P<slug>[-\w]+)/location/new/$', fblocation_form, name="fblocation_new"),
    url(r'^foodbank/(?P<slug>[-\w]+)/location/(?P<loc_slug>[-\w]+)/edit/$', fblocation_form, name="fblocation_edit"),
    url(r'^foodbank/(?P<slug>[-\w]+)/location/(?P<loc_slug>[-\w]+)/delete/$', fblocation_delete, name="fblocation_delete"),
    url(r'^foodbank/(?P<slug>[-\w]+)/location/(?P<loc_slug>[-\w]+)/politics/edit/$', fblocation_politics_edit, name="fblocation_politics_edit"),
    url(r'^foodbank/(?P<slug>[-\w]+)/politics/edit/$', foodbank_politics_form, name="foodbank_politics_edit"),

    url(r'^need/new/$', need_form, name="newneed"),
    url(r'^need/(?P<id>\b[0-9a-f]{8}\b)/$', need, name="need"),
    url(r'^need/(?P<id>\b[0-9a-f]{8}\b)/edit/$', need_form, name="need_form"),
    url(r'^need/(?P<id>\b[0-9a-f]{8}\b)/delete/$', need_delete, name="need_delete"),
    url(r'^need/(?P<id>\b[0-9a-f]{8}\b)/(?P<action>publish|unpublish)/$', need_publish, name="need_publish"),
    url(r'^need/(?P<id>\b[0-9a-f]{8}\b)/notifications/$', need_notifications, name="need_notifications"),

    url(r'^locations/$', locations, name="locations"),
    url(r'^locations/loader/sa/$', locations_loader_sa, name="locations_loader_sa"),

    url(r'^parlcon/new/$', parlcon_form, name="parlcon_form"),
    url(r'^parlcon/loader/$', parlcon_loader, name="parlcon_loader"),
    url(r'^parlcon/loader/geojson/$', parlcon_loader_geojson, name="parlcon_loader_geojson"),
    url(r'^parlcon/loader/centre/$', parlcon_loader_centre, name="parlcon_loader_centre"),
    url(r'^parlcon/loader/twitter/$', parlcon_loader_twitter_handle, name="parlcon_loader_twitter_handle"),
    url(r'^parlcon/(?P<slug>[-\w]+)/edit/$', parlcon_form, name="parlcon_form"),

    url(r'^politics/$', politics, name="politics"),
    url(r'^politics/csv/$', politics_csv, name="politics_csv"),

    url(r'^settings/$', settings, name="settings"),
    url(r'^order-groups/$', order_groups, name="order_groups"),
    url(r'^order-group/(?P<slug>[-\w]+)/$', order_group, name="order_group"),
    url(r'^order-group/(?P<slug>[-\w]+)/edit/$', order_group_form, name="order_group_edit"),
    url(r'^order-groups/new/$', order_group_form, name="order_group_new"),
    url(r'^credentials/$', credentials, name="credentials"),
    url(r'^credentials/new/$', credentials_form, name="credential_new"),
    url(r'^searches/$', searches, name="searches"),
    url(r'^searches/csv/$', searches_csv, name="searches_csv"),
    url(r'^map/$', map, name="map"),
    url(r'^search/$', search_results, name="search_results"),
    url(r'^stats/$', stats, name="stats"),
    url(r'^subscriptions/$', subscriptions, name="subscriptions"),
    url(r'^subscription/delete/$', delete_subscription, name="delete_subscription"),
    url(r'^clearcache/$', clearcache, name="clearcache"),

    url(r'^test_order_email/(?P<id>[-\w]+)/$', test_order_email, name="test_order_email"),
    url(r'^resaver/orders/$', resave_orders, name="resave_orders"),
)
