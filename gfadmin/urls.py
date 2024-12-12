from django.urls import re_path
from gfadmin.views import *

app_name = "gfadmin"

urlpatterns = (

    re_path(r'^$', index, name="index"),

    re_path(r'^order/new/$', order_form, name="neworder"),
    re_path(r'^order/(?P<id>[-\w]+)/$', order, name="order"),
    re_path(r'^order/(?P<id>[-\w]+)/edit/$', order_form, name="order_edit"),
    re_path(r'^order/(?P<id>[-\w]+)/sendnotification/$', order_send_notification, name="order_send_notification"),
    re_path(r'^order/(?P<id>[-\w]+)/delete/$', order_delete, name="order_delete"),
    re_path(r'^order/(?P<id>[-\w]+)/email/$', order_email, name="order_email"),

    re_path(r'^foodbanks/$', foodbanks, name="foodbanks"),
    re_path(r'^foodbanks/christmascards/$', foodbanks_christmascards, name="foodbanks_christmascards"),
    re_path(r'^foodbanks/delivery_addresses/$', foodbanks_delivery_addresses, name="foodbanks_delivery_addresses"),
    re_path(r'^foodbanks/dupe_postcodes/$', foodbanks_dupe_postcodes, name="foodbanks_dupe_postcodes"),
    re_path(r'^foodbanks/csv/$', foodbanks_csv, name="foodbanks_csv"),
    re_path(r'^foodbanks/without_need/$', foodbanks_without_need, name="foodbanks_without_need"),

    re_path(r'^orders/$', orders, name="orders"),
    re_path(r'^orders/csv/$', orders_csv, name="orders_csv"),

    re_path(r'^needs/$', needs, name="needs"),
    re_path(r'^needs/otherlines/$', needs_otherlines, name="needs_otherlines"),
    re_path(r'^needs/deleteall/$', needs_deleteall, name="needs_deleteall"),
    re_path(r'^needs/csv/$', needs_csv, name="needs_csv"),

    re_path(r'^items/$', items, name="items"),
    re_path(r'^item/new/$', item_form, name="item_new"),
    re_path(r'^item/(?P<slug>[-\w]+)/edit/$', item_form, name="item_form"),

    re_path(r'^foodbank/new/$', foodbank_form, name="foodbank_new"),
    re_path(r'^foodbank/(?P<slug>[-\w]+)/$', foodbank, name="foodbank"),
    re_path(r'^foodbank/(?P<slug>[-\w]+)/edit/$', foodbank_form, name="foodbank_edit"),

    re_path(r'^foodbank/(?P<slug>[-\w]+)/donationpoint/new/$', donationpoint_form, name="donationpoint_new"),
    re_path(r'^foodbank/(?P<slug>[-\w]+)/donationpoint/(?P<dp_slug>[-\w]+)/edit/$', donationpoint_form, name="donationpoint_edit"),
    re_path(r'^foodbank/(?P<slug>[-\w]+)/donationpoint/(?P<dp_slug>[-\w]+)/delete/$', donationpoint_delete, name="donationpoint_delete"),

    re_path(r'^foodbank/(?P<slug>[-\w]+)/location/new/$', fblocation_form, name="fblocation_new"),
    re_path(r'^foodbank/(?P<slug>[-\w]+)/location/(?P<loc_slug>[-\w]+)/edit/$', fblocation_form, name="fblocation_edit"),
    re_path(r'^foodbank/(?P<slug>[-\w]+)/location/(?P<loc_slug>[-\w]+)/delete/$', fblocation_delete, name="fblocation_delete"),
    re_path(r'^foodbank/(?P<slug>[-\w]+)/location/(?P<loc_slug>[-\w]+)/politics/edit/$', fblocation_politics_edit, name="fblocation_politics_edit"),

    re_path(r'^foodbank/(?P<slug>[-\w]+)/politics/edit/$', foodbank_politics_form, name="foodbank_politics_edit"),
    re_path(r'^foodbank/(?P<slug>[-\w]+)/crawl/$', foodbank_crawl, name="foodbank_crawl"),
    re_path(r'^foodbank/(?P<slug>[-\w]+)/sendrfi/$', foodbank_rfi, name="foodbank_rfi"),
    re_path(r'^foodbank/(?P<slug>[-\w]+)/delete/$', foodbank_delete, name="foodbank_delete"),

    re_path(r'^need/new/$', need_form, name="newneed"),
    re_path(r'^need/(?P<id>\b[0-9a-f]{8}\b)/$', need, name="need"),
    re_path(r'^need/(?P<id>\b[0-9a-f]{8}\b)/edit/$', need_form, name="need_form"),
    re_path(r'^need/(?P<id>\b[0-9a-f]{8}\b)/nonpertinent/$', need_nonpertinent, name="need_nonpertinent"),
    re_path(r'^need/(?P<id>\b[0-9a-f]{8}\b)/delete/$', need_delete, name="need_delete"),
    re_path(r'^need/(?P<id>\b[0-9a-f]{8}\b)/(?P<action>publish|unpublish)/$', need_publish, name="need_publish"),
    re_path(r'^need/(?P<id>\b[0-9a-f]{8}\b)/notifications/$', need_notifications, name="need_notifications"),
    re_path(r'^need/(?P<id>\b[0-9a-f]{8}\b)/email/$', need_email, name="need_email"),
    re_path(r'^need/(?P<id>\b[0-9a-f]{8}\b)/categorise/$', need_categorise, name="need_categorise"),
    re_path(r'^need/(?P<id>\b[0-9a-f]{8}\b)/line/(?P<line_id>\d+)/$', needline_form, name="needline_form"),

    re_path(r'^locations/$', locations, name="locations"),
    re_path(r'^locations/loader/sa/$', locations_loader_sa, name="locations_loader_sa"),

    re_path(r'^discrepancy/(?P<id>[-\w]+)/$', discrepancy, name="discrepancy"),
    re_path(r'^discrepancy/(?P<id>[-\w]+)/action/$', discrepancy_action, name="discrepancy_action"),

    re_path(r'^donationpoints/$', donationpoints, name="donationpoints"), 

    re_path(r'^parlcon/new/$', parlcon_form, name="parlcon_form"),
    re_path(r'^parlcon/loader/$', parlcon_loader, name="parlcon_loader"),
    re_path(r'^parlcon/loader/geojson/$', parlcon_loader_geojson, name="parlcon_loader_geojson"),
    re_path(r'^parlcon/loader/centre/$', parlcon_loader_centre, name="parlcon_loader_centre"),
    re_path(r'^parlcon/loader/twitter/$', parlcon_loader_twitter_handle, name="parlcon_loader_twitter_handle"),
    re_path(r'^parlcon/(?P<slug>[-\w]+)/edit/$', parlcon_form, name="parlcon_form"),

    re_path(r'^places/$', places, name="places"),
    re_path(r'^places/loader/$', places_loader, name="places_loader"),

    re_path(r'^finder/$', finder, name="finder"),
    re_path(r'^finder/check/$', finder_check, name="finder_check"),

    re_path(r'^politics/$', politics, name="politics"),
    re_path(r'^politics/csv/$', politics_csv, name="politics_csv"),

    re_path(r'^settings/$', settings, name="settings"),
    re_path(r'^order-groups/$', order_groups, name="order_groups"),
    re_path(r'^order-group/(?P<slug>[-\w]+)/$', order_group, name="order_group"),
    re_path(r'^order-group/(?P<slug>[-\w]+)/edit/$', order_group_form, name="order_group_edit"),
    re_path(r'^order-groups/new/$', order_group_form, name="order_group_new"),

    re_path(r'^foodbank-groups/$', foodbank_groups, name="foodbank_groups"),
    re_path(r'^foodbank-group/(?P<slug>[-\w]+)/$', foodbank_group, name="foodbank_group"),
    re_path(r'^foodbank-group/(?P<slug>[-\w]+)/edit/$', foodbank_group_form, name="foodbank_group_edit"),
    re_path(r'^foodbank-groups/new/$', foodbank_group_form, name="foodbank_group_new"),

    re_path(r'^credentials/$', credentials, name="credentials"),
    re_path(r'^credentials/new/$', credentials_form, name="credential_new"),

    re_path(r'^search/$', search_results, name="search_results"),

    re_path(r'^subscriptions/$', subscriptions, name="subscriptions"),
    re_path(r'^subscriptions/csv/$', subscriptions_csv, name="subscriptions_csv"),
    re_path(r'^subscription/delete/$', delete_subscription, name="delete_subscription"),

    re_path(r'^clearcache/$', clearcache, name="clearcache"),
    re_path(r'^emailtester/$', email_tester, name="email_tester"),
    re_path(r'^emailtester/test/$', email_tester_test, name="email_tester_test"),

    re_path(r'^stats/quarter/$', quarter_stats, name="quarter_stats"),
    re_path(r'^stats/orders/$', order_stats, name="order_stats"),
    re_path(r'^stats/editing/$', edit_stats, name="edit_stats"),
    re_path(r'^stats/subscribers/$', subscriber_stats, name="subscriber_stats"),
    re_path(r'^stats/subscribers/graph/$', subscriber_graph, name="subscriber_graph"),
    re_path(r'^stats/finder/$', finder_stats, name="finder_stats"),
    re_path(r'^stats/needs/$', need_stats, name="need_stats"),

    re_path(r'^proxy/$', proxy, name="proxy"),
    re_path(r'^proxy/gmaps/(?P<type>textsearch|placedetails)/$', gmap_proxy, name="gmap_proxy"),

    re_path(r'^resaver/orders/$', resave_orders, name="resave_orders"),
)
