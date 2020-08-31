from django.conf import settings
from django.conf.urls import include, url
from django.conf.urls.static import static
from django.contrib.staticfiles.views import serve
from django.views.generic import RedirectView

import givefood.views
from givefood.const.general import RICK_ASTLEY

import session_csrf
session_csrf.monkeypatch()

from django.contrib import admin
admin.autodiscover()

urlpatterns = (
    url(r'^_ah/', include('djangae.urls')),

    # PUBLIC
    url(r'^$', givefood.views.public_index, name="public_index"),
    url(r'^api/$', givefood.views.public_api, name="public_api"),
    url(r'^articles/(?P<slug>[-\w]+)/$', givefood.views.public_article, name="public_article"),
    url(r'^(?P<year>(2019))/$', givefood.views.public_annual_report, name="public_annual_report"),
    url(r'^register-foodbank/$', givefood.views.public_reg_foodbank, name="public_reg_foodbank"),
    url(r'^sitemap.xml$', givefood.views.public_sitemap, name="public_sitemap"),

    # KINDA PUBLIC
    url(r'^precacher/$', givefood.views.precacher, name="precacher"),
    url(r'^generate-(?P<year>(2019))/$', givefood.views.public_gen_annual_report, name="public_gen_annual_report"),
    url(r'^productimage/$', givefood.views.public_product_image, name="public_product_image"),
    url(r'^distill_webhook/$', givefood.views.distill_webhook, name="distill_webhook"),

    # WFBN
    url(r'^what-food-banks-need/$', RedirectView.as_view(url='/needs/')),
    url(r'^needs/$', givefood.views.public_what_food_banks_need, name="public_what_food_banks_need"),
    url(r'^needs/click/(?P<slug>[-\w]+)/$', givefood.views.public_what_food_banks_need_click, name="public_what_food_banks_need_click"),
    url(r'^needs/at/(?P<slug>[-\w]+)/$', givefood.views.public_wfbn_foodbank, name="public_wfbn_foodbank"),
    url(r'^needs/at/(?P<slug>[-\w]+)/map.png$', givefood.views.public_wfbn_foodbank_map, name="public_wfbn_foodbank_map"),
    url(r'^needs/in/constituencies/$', givefood.views.public_wfbn_constituencies, name="public_wfbn_constituencies"),
    url(r'^needs/in/constituency/$', RedirectView.as_view(url="/needs/in/constituencies/")),
    url(r'^needs/in/constituency/(?P<slug>[-\w]+)/$', givefood.views.public_wfbn_constituency, name="public_wfbn_constituency"),

    # Rickrolling
    url(r'^wp-login\.php$', RedirectView.as_view(url=RICK_ASTLEY)),

    # ADMIN
    url(r'^admin/$', givefood.views.admin_index, name="admin_index"),

    url(r'^admin/order/new/$', givefood.views.admin_order_form, name="admin_neworder"),
    url(r'^admin/order/(?P<id>[-\w]+)/$', givefood.views.admin_order, name="admin_order"),
    url(r'^admin/order/(?P<id>[-\w]+)/edit/$', givefood.views.admin_order_form, name="admin_order_edit"),
    url(r'^admin/order/(?P<id>[-\w]+)/sendnotification/$', givefood.views.admin_order_send_notification, name="admin_order_send_notification"),

    url(r'^admin/foodbanks/$', givefood.views.admin_foodbanks, name="admin_foodbanks"),
    url(r'^admin/foodbanks/christmascards/$', givefood.views.admin_foodbanks_christmascards, name="admin_foodbanks_christmascards"),
    url(r'^admin/foodbanks/csv/$', givefood.views.admin_foodbanks_csv, name="admin_foodbanks_csv"),
    url(r'^admin/orders/$', givefood.views.admin_orders, name="admin_orders"),
    url(r'^admin/orders/csv/$', givefood.views.admin_orders_csv, name="admin_orders_csv"),
    url(r'^admin/needs/$', givefood.views.admin_needs, name="admin_needs"),
    url(r'^admin/needs/csv/$', givefood.views.admin_needs_csv, name="admin_needs_csv"),

    url(r'^admin/foodbank/new/$', givefood.views.admin_foodbank_form, name="admin_newfoodbank"),
    url(r'^admin/foodbank/(?P<slug>[-\w]+)/$', givefood.views.admin_foodbank, name="admin_foodbank"),
    url(r'^admin/foodbank/(?P<slug>[-\w]+)/edit/$', givefood.views.admin_foodbank_form, name="admin_foodbank_edit"),
    url(r'^admin/foodbank/(?P<slug>[-\w]+)/location/new/$', givefood.views.admin_fblocation_form, name="admin_fblocation_new"),
    url(r'^admin/foodbank/(?P<slug>[-\w]+)/location/(?P<loc_slug>[-\w]+)/edit/$', givefood.views.admin_fblocation_form, name="admin_fblocation_edit"),
    url(r'^admin/foodbank/(?P<slug>[-\w]+)/location/(?P<loc_slug>[-\w]+)/politics/edit/$', givefood.views.admin_fblocation_politics_edit, name="admin_fblocation_politics_edit"),
    url(r'^admin/foodbank/(?P<slug>[-\w]+)/find-locations/$', givefood.views.admin_findlocations, name="admin_findlocations"),
    url(r'^admin/foodbank/(?P<slug>[-\w]+)/politics/edit/$', givefood.views.admin_foodbank_politics_form, name="admin_foodbank_politics_edit"),

    url(r'^admin/need/new/$', givefood.views.admin_need_form, name="admin_newneed"),
    url(r'^admin/need/(?P<id>\b[0-9a-f]{8}\b)/$', givefood.views.admin_need, name="admin_need"),
    url(r'^admin/need/(?P<id>\b[0-9a-f]{8}\b)/edit/$', givefood.views.admin_need_form, name="admin_need_form"),
    url(r'^admin/need/(?P<id>\b[0-9a-f]{8}\b)/delete/$', givefood.views.admin_need_delete, name="admin_need_delete"),
    url(r'^admin/need/(?P<id>\b[0-9a-f]{8}\b)/publish/$', givefood.views.admin_need_publish, name="admin_need_publish"),
    url(r'^admin/need/(?P<id>\b[0-9a-f]{8}\b)/tweet/$', givefood.views.admin_need_tweet, name="admin_need_tweet"),

    url(r'^admin/locations/$', givefood.views.admin_locations, name="admin_locations"),
    url(r'^admin/politics/$', givefood.views.admin_politics, name="admin_politics"),
    url(r'^admin/searches/$', givefood.views.admin_searches, name="admin_searches"),
    url(r'^admin/searches/csv/$', givefood.views.admin_searches_csv, name="admin_searches_csv"),
    url(r'^admin/map/$', givefood.views.admin_map, name="admin_map"),
    url(r'^admin/search/$', givefood.views.admin_search, name="admin_search"),
    url(r'^admin/stats/$', givefood.views.admin_stats, name="admin_stats"),

    url(r'^admin/test_order_email/(?P<id>[-\w]+)/$', givefood.views.admin_test_order_email, name="admin_test_order_email"),
    url(r'^admin/resaver/orders/$', givefood.views.admin_resave_orders, name="admin_resave_orders"),

    url(r'^api/1/foodbanks/$', givefood.views.api_foodbanks, name="api_foodbanks"),
    url(r'^api/1/foodbanks/search/$', givefood.views.api_foodbank_search, name="api_foodbank_search"),
    url(r'^api/1/foodbank/(?P<slug>[-\w]+)/$', givefood.views.api_foodbank, name="api_foodbank"),
    url(r'^api/1/foodbank/$', givefood.views.api_foodbank_key, name="api_foodbank_key"),
    url(r'^api/1/needs/$', givefood.views.api_needs, name="api_needs"),
    url(r'^api/1/need/(?P<id>\b[0-9a-f]{8}\b)/$', givefood.views.api_need, name="api_need"),

    url(r'^api/2/', include('gfapi2.urls')),

    url(r'^csp/', include('cspreports.urls')),
    url(r'^auth/', include('djangae.contrib.gauth.urls')),
)

if settings.DEBUG:
    urlpatterns += tuple(static(settings.STATIC_URL, view=serve, show_indexes=True))
