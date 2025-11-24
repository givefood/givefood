from django.urls import path, re_path
from gfadmin.views import *

app_name = "gfadmin"

urlpatterns = (

    path("", index, name="index"),

    path("order/new/", order_form, name="neworder"),
    path("order/<slug:id>/", order, name="order"),
    path("order/<slug:id>/edit/", order_form, name="order_edit"),
    path("order/<slug:id>/sendnotification/", order_send_notification, name="order_send_notification"),
    path("order/<slug:id>/delete/", order_delete, name="order_delete"),
    path("order/<slug:id>/email/", order_email, name="order_email"),

    path("foodbanks/", foodbanks, name="foodbanks"),
    path("foodbanks/dupe_postcodes/", foodbanks_dupe_postcodes, name="foodbanks_dupe_postcodes"),
    path("foodbanks/csv/", foodbanks_csv, name="foodbanks_csv"),
    path("foodbanks/without_need/", foodbanks_without_need, name="foodbanks_without_need"),

    path("orders/", orders, name="orders"),
    path("orders/csv/", orders_csv, name="orders_csv"),

    path("needs/", needs, name="needs"),
    path("needs/otherlines/", needs_otherlines, name="needs_otherlines"),
    path("needs/deleteall/", needs_deleteall, name="needs_deleteall"),
    path("needs/csv/", needs_csv, name="needs_csv"),

    path("items/", items, name="items"),
    path("item/new/", item_form, name="item_new"),
    path("item/<slug:slug>/edit/", item_form, name="item_form"),

    path("slug-redirects/", slug_redirects, name="slug_redirects"),
    path("slug-redirect/new/", slug_redirect_form, name="slug_redirect_new"),
    path("slug-redirect/<int:id>/edit/", slug_redirect_form, name="slug_redirect_form"),

    path("foodbank/new/", foodbank_form, name="foodbank_new"),
    path("foodbank/<slug:slug>/", foodbank, name="foodbank"),
    path("foodbank/<slug:slug>/edit/", foodbank_form, name="foodbank_edit"),
    path("foodbank/<slug:slug>/check/", foodbank_check, name="foodbank_check"),

    path("foodbank/<slug:slug>/donationpoint/new/", donationpoint_form, name="donationpoint_new"),
    path("foodbank/<slug:slug>/donationpoint/<slug:dp_slug>/edit/", donationpoint_form, name="donationpoint_edit"),
    path("foodbank/<slug:slug>/donationpoint/<slug:dp_slug>/delete/", donationpoint_delete, name="donationpoint_delete"),

    path("foodbank/<slug:slug>/location/new/", fblocation_form, name="fblocation_new"),
    path("foodbank/<slug:slug>/location/new/area/", fblocation_area_form, name="fblocation_area_new"),
    path("foodbank/<slug:slug>/location/<slug:loc_slug>/edit/", fblocation_form, name="fblocation_edit"),
    path("foodbank/<slug:slug>/location/<slug:loc_slug>/delete/", fblocation_delete, name="fblocation_delete"),
    path("foodbank/<slug:slug>/location/<slug:loc_slug>/politics/edit/", fblocation_politics_edit, name="fblocation_politics_edit"),

    path("foodbank/<slug:slug>/politics/edit/", foodbank_politics_form, name="foodbank_politics_edit"),
    path("foodbank/<slug:slug>/edit/urls/", foodbank_urls_form, name="foodbank_urls_edit"),
    path("foodbank/<slug:slug>/addsub/", foodbank_addsub, name="foodbank_addsub"),
    path("foodbank/<slug:slug>/crawl/", foodbank_crawl, name="foodbank_crawl"),
    path("foodbank/<slug:slug>/sendrfi/", foodbank_rfi, name="foodbank_rfi"),
    path("foodbank/<slug:slug>/resave/", foodbank_resave, name="foodbank_resave"),
    path("foodbank/<slug:slug>/touch/", foodbank_touch, name="foodbank_touch"),
    path("foodbank/<slug:slug>/delete/", foodbank_delete, name="foodbank_delete"),

    path("need/new", need_form, name="newneed"),
    path("need/<uuid:id>/", need, name="need"),
    path("need/<uuid:id>/edit/", need_form, name="need_form"),
    path("need/<uuid:id>/nonpertinent/", need_nonpertinent, name="need_nonpertinent"),
    path("need/<uuid:id>/delete/", need_delete, name="need_delete"),
    path("need/<uuid:id>/notifications/", need_notifications, name="need_notifications"),
    path("need/<uuid:id>/translations/", need_translations, name="need_translations"),
    path("need/<uuid:id>/email/", need_email, name="need_email"),
    path("need/<uuid:id>/categorise/", need_categorise, name="need_categorise"),
    path("need/<uuid:id>/line/<int:line_id>/", needline_form, name="needline_form"),
    path("need/<uuid:id>/<slug:action>/", need_publish, name="need_publish"),

    path("locations/", locations, name="locations"),
    path("locations/loader/sa/", locations_loader_sa, name="locations_loader_sa"),

    path("discrepancy/<slug:id>/", discrepancy, name="discrepancy"),
    path("discrepancy/<slug:id>/action/", discrepancy_action, name="discrepancy_action"),

    path("donationpoints/", donationpoints, name="donationpoints"), 

    path("parlcon/new/", parlcon_form, name="parlcon_form"),
    path("parlcon/loader/", parlcon_loader, name="parlcon_loader"),
    path("parlcon/loader/geojson/", parlcon_loader_geojson, name="parlcon_loader_geojson"),
    path("parlcon/loader/centre/", parlcon_loader_centre, name="parlcon_loader_centre"),
    path("parlcon/loader/twitter/", parlcon_loader_twitter_handle, name="parlcon_loader_twitter_handle"),
    path("parlcon/<slug:slug>/edit/", parlcon_form, name="parlcon_form"),

    path("places/", places, name="places"),
    path("places/loader/", places_loader, name="places_loader"),

    path("finder/", finder, name="finder"),
    path("finder/check/", finder_check, name="finder_check"),
    path("finder/trussell/", finder_trussell, name="finder_trussell"),
    path("finder/fsa/", finder_fsa, name="finder_fsa"),

    path("politics/", politics, name="politics"),
    path("politics/csv/", politics_csv, name="politics_csv"),

    path("settings/", settings, name="settings"),
    path("order-groups/", order_groups, name="order_groups"),
    path("order-group/<slug:slug>/", order_group, name="order_group"),
    path("order-group/<slug:slug>/edit/", order_group_form, name="order_group_edit"),
    path("order-groups/new/", order_group_form, name="order_group_new"),

    path("foodbank-groups/", foodbank_groups, name="foodbank_groups"),
    path("foodbank-group/<slug:slug>/", foodbank_group, name="foodbank_group"),
    path("foodbank-group/<slug:slug>/edit/", foodbank_group_form, name="foodbank_group_edit"),
    path("foodbank-groups/new/", foodbank_group_form, name="foodbank_group_new"),

    path("credentials/", credentials, name="credentials"),
    path("credentials/new/", credentials_form, name="credential_new"),

    path("search/", search_results, name="search_results"),

    path("subscriptions/", subscriptions, name="subscriptions"),
    path("subscriptions/csv/", subscriptions_csv, name="subscriptions_csv"),
    path("subscription/delete/", delete_subscription, name="delete_subscription"),

    path("clearcache/", clearcache, name="clearcache"),
    path("emailtester/", email_tester, name="email_tester"),
    path("emailtester/test/", email_tester_test, name="email_tester_test"),

    path("changelog/", changelog, name="changelog"),

    path("crawl-sets/", crawl_sets, name="crawl_sets"),
    path("crawl-set/<int:crawl_set_id>/", crawl_set, name="crawl_set"),

    path("stats/quarter/", quarter_stats, name="quarter_stats"),
    path("stats/orders/", order_stats, name="order_stats"),
    path("stats/editing/", edit_stats, name="edit_stats"),
    path("stats/subscribers/", subscriber_stats, name="subscriber_stats"),
    path("stats/subscribers/graph/", subscriber_graph, name="subscriber_graph"),
    path("stats/finder/", finder_stats, name="finder_stats"),
    path("stats/needs/", need_stats, name="need_stats"),

    path("proxy/", proxy, name="proxy"),
    re_path(r'^proxy/gmaps/(?P<type>textsearch|placedetails)/$', gmap_proxy, name="gmap_proxy"),
    
)
