from django.conf.urls import url
from gfadmin.views import *

app_name = "gfadmin"

urlpatterns = (

    url(r'^$', index, name="index"),

    url(r'^order/new/$', order_form, name="neworder"),
    url(r'^order/(?P<id>[-\w]+)/$', order, name="order"),
    url(r'^order/(?P<id>[-\w]+)/edit/$', order_form, name="order_edit"),
    url(r'^order/(?P<id>[-\w]+)/sendnotification/$', order_send_notification, name="order_send_notification"),
    url(r'^order/(?P<id>[-\w]+)/delete/$', order_delete, name="order_delete"),
    url(r'^order/(?P<id>[-\w]+)/email/$', order_email, name="order_email"),

    url(r'^foodbanks/$', foodbanks, name="foodbanks"),
    url(r'^foodbanks/christmascards/$', foodbanks_christmascards, name="foodbanks_christmascards"),
    url(r'^foodbanks/delivery_addresses/$', foodbanks_delivery_addresses, name="foodbanks_delivery_addresses"),
    url(r'^foodbanks/dupe_postcodes/$', foodbanks_dupe_postcodes, name="foodbanks_dupe_postcodes"),
    url(r'^foodbanks/csv/$', foodbanks_csv, name="foodbanks_csv"),
    url(r'^foodbanks/without_need/$', foodbanks_without_need, name="foodbanks_without_need"),

    url(r'^orders/$', orders, name="orders"),
    url(r'^orders/csv/$', orders_csv, name="orders_csv"),

    url(r'^needs/$', needs, name="needs"),
    url(r'^needs/otherlines/$', needs_otherlines, name="needs_otherlines"),
    url(r'^needs/deleteall/$', needs_deleteall, name="needs_deleteall"),
    url(r'^needs/csv/$', needs_csv, name="needs_csv"),

    url(r'^items/$', items, name="items"),
    url(r'^item/new/$', item_form, name="item_new"),
    url(r'^item/(?P<slug>[-\w]+)/edit/$', item_form, name="item_form"),

    url(r'^foodbank/new/$', foodbank_form, name="foodbank_new"),
    url(r'^foodbank/(?P<slug>[-\w]+)/$', foodbank, name="foodbank"),
    url(r'^foodbank/(?P<slug>[-\w]+)/edit/$', foodbank_form, name="foodbank_edit"),

    url(r'^foodbank/(?P<slug>[-\w]+)/donationpoint/new/$', donationpoint_form, name="donationpoint_new"),
    url(r'^foodbank/(?P<slug>[-\w]+)/donationpoint/(?P<dp_slug>[-\w]+)/edit/$', donationpoint_form, name="donationpoint_edit"),
    url(r'^foodbank/(?P<slug>[-\w]+)/donationpoint/(?P<dp_slug>[-\w]+)/delete/$', donationpoint_delete, name="donationpoint_delete"),

    url(r'^foodbank/(?P<slug>[-\w]+)/location/new/$', fblocation_form, name="fblocation_new"),
    url(r'^foodbank/(?P<slug>[-\w]+)/location/(?P<loc_slug>[-\w]+)/edit/$', fblocation_form, name="fblocation_edit"),
    url(r'^foodbank/(?P<slug>[-\w]+)/location/(?P<loc_slug>[-\w]+)/delete/$', fblocation_delete, name="fblocation_delete"),
    url(r'^foodbank/(?P<slug>[-\w]+)/location/(?P<loc_slug>[-\w]+)/politics/edit/$', fblocation_politics_edit, name="fblocation_politics_edit"),

    url(r'^foodbank/(?P<slug>[-\w]+)/politics/edit/$', foodbank_politics_form, name="foodbank_politics_edit"),
    url(r'^foodbank/(?P<slug>[-\w]+)/crawl/$', foodbank_crawl, name="foodbank_crawl"),
    url(r'^foodbank/(?P<slug>[-\w]+)/sendrfi/$', foodbank_rfi, name="foodbank_rfi"),
    url(r'^foodbank/(?P<slug>[-\w]+)/delete/$', foodbank_delete, name="foodbank_delete"),

    url(r'^need/new/$', need_form, name="newneed"),
    url(r'^need/(?P<id>\b[0-9a-f]{8}\b)/$', need, name="need"),
    url(r'^need/(?P<id>\b[0-9a-f]{8}\b)/edit/$', need_form, name="need_form"),
    url(r'^need/(?P<id>\b[0-9a-f]{8}\b)/delete/$', need_delete, name="need_delete"),
    url(r'^need/(?P<id>\b[0-9a-f]{8}\b)/(?P<action>publish|unpublish)/$', need_publish, name="need_publish"),
    url(r'^need/(?P<id>\b[0-9a-f]{8}\b)/notifications/$', need_notifications, name="need_notifications"),
    url(r'^need/(?P<id>\b[0-9a-f]{8}\b)/email/$', need_email, name="need_email"),
    url(r'^need/(?P<id>\b[0-9a-f]{8}\b)/categorise/$', need_categorise, name="need_categorise"),
    url(r'^need/(?P<id>\b[0-9a-f]{8}\b)/line/(?P<line_id>\d+)/$', needline_form, name="needline_form"),

    url(r'^locations/$', locations, name="locations"),
    url(r'^locations/loader/sa/$', locations_loader_sa, name="locations_loader_sa"),

    url(r'^discrepancy/(?P<id>[-\w]+)/$', discrepancy, name="discrepancy"),
    url(r'^discrepancy/(?P<id>[-\w]+)/action/$', discrepancy_action, name="discrepancy_action"),

    url(r'^donationpoints/$', donationpoints, name="donationpoints"), 

    url(r'^parlcon/new/$', parlcon_form, name="parlcon_form"),
    url(r'^parlcon/loader/$', parlcon_loader, name="parlcon_loader"),
    url(r'^parlcon/loader/geojson/$', parlcon_loader_geojson, name="parlcon_loader_geojson"),
    url(r'^parlcon/loader/centre/$', parlcon_loader_centre, name="parlcon_loader_centre"),
    url(r'^parlcon/loader/twitter/$', parlcon_loader_twitter_handle, name="parlcon_loader_twitter_handle"),
    url(r'^parlcon/(?P<slug>[-\w]+)/edit/$', parlcon_form, name="parlcon_form"),

    url(r'^places/$', places, name="places"),
    url(r'^places/loader/$', places_loader, name="places_loader"),

    url(r'^finder/$', finder, name="finder"),
    url(r'^finder/check/$', finder_check, name="finder_check"),

    url(r'^politics/$', politics, name="politics"),
    url(r'^politics/csv/$', politics_csv, name="politics_csv"),

    url(r'^settings/$', settings, name="settings"),
    url(r'^order-groups/$', order_groups, name="order_groups"),
    url(r'^order-group/(?P<slug>[-\w]+)/$', order_group, name="order_group"),
    url(r'^order-group/(?P<slug>[-\w]+)/edit/$', order_group_form, name="order_group_edit"),
    url(r'^order-groups/new/$', order_group_form, name="order_group_new"),

    url(r'^foodbank-groups/$', foodbank_groups, name="foodbank_groups"),
    url(r'^foodbank-group/(?P<slug>[-\w]+)/$', foodbank_group, name="foodbank_group"),
    url(r'^foodbank-group/(?P<slug>[-\w]+)/edit/$', foodbank_group_form, name="foodbank_group_edit"),
    url(r'^foodbank-groups/new/$', foodbank_group_form, name="foodbank_group_new"),

    url(r'^credentials/$', credentials, name="credentials"),
    url(r'^credentials/new/$', credentials_form, name="credential_new"),

    url(r'^search/$', search_results, name="search_results"),

    url(r'^subscriptions/$', subscriptions, name="subscriptions"),
    url(r'^subscriptions/csv/$', subscriptions_csv, name="subscriptions_csv"),
    url(r'^subscription/delete/$', delete_subscription, name="delete_subscription"),

    url(r'^clearcache/$', clearcache, name="clearcache"),
    url(r'^emailtester/$', email_tester, name="email_tester"),
    url(r'^emailtester/test/$', email_tester_test, name="email_tester_test"),

    url(r'^stats/quarter/$', quarter_stats, name="quarter_stats"),
    url(r'^stats/orders/$', order_stats, name="order_stats"),
    url(r'^stats/editing/$', edit_stats, name="edit_stats"),
    url(r'^stats/subscribers/$', subscriber_stats, name="subscriber_stats"),
    url(r'^stats/subscribers/graph/$', subscriber_graph, name="subscriber_graph"),
    url(r'^stats/finder/$', finder_stats, name="finder_stats"),
    url(r'^stats/needs/$', need_stats, name="need_stats"),

    url(r'^proxy/$', proxy, name="proxy"),
    url(r'^proxy/gmaps/(?P<type>textsearch|placedetails)/$', gmap_proxy, name="gmap_proxy"),

    url(r'^resaver/orders/$', resave_orders, name="resave_orders"),
)
