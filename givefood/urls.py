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
    url(r'^privacy/$', givefood.views.public_privacy, name="public_privacy"),

    # KINDA PUBLIC
    url(r'^precacher/$', givefood.views.precacher, name="precacher"),
    url(r'^generate-(?P<year>(2019))/$', givefood.views.public_gen_annual_report, name="public_gen_annual_report"),
    url(r'^productimage/$', givefood.views.public_product_image, name="public_product_image"),
    url(r'^distill_webhook/$', givefood.views.distill_webhook, name="distill_webhook"),

    # WFBN
    url(r'^needs/tt-old-data/$', givefood.views.public_tt_old_data, name="public_tt_old_data"),
    url(r'^needs/$', givefood.views.public_what_food_banks_need, name="public_what_food_banks_need"),
    url(r'^needs/click/(?P<slug>[-\w]+)/$', givefood.views.public_what_food_banks_need_click, name="public_what_food_banks_need_click"),

    url(r'^needs/at/(?P<slug>[-\w]+)/$', givefood.views.public_wfbn_foodbank, name="public_wfbn_foodbank"),
    url(r'^needs/at/(?P<slug>[-\w]+)/map.png$', givefood.views.public_wfbn_foodbank_map, name="public_wfbn_foodbank_map"),
    url(r'^needs/at/(?P<slug>[-\w]+)/(?P<locslug>[-\w]+)/$', givefood.views.public_wfbn_foodbank_location, name="public_wfbn_foodbank_location"),
    url(r'^needs/at/(?P<slug>[-\w]+)/(?P<locslug>[-\w]+)/map.png$', givefood.views.public_wfbn_foodbank_location_map, name="public_wfbn_foodbank_location_map"),

    url(r'^needs/in/constituencies/$', givefood.views.public_wfbn_constituencies, name="public_wfbn_constituencies"),
    url(r'^needs/in/constituency/$', RedirectView.as_view(url="/needs/in/constituencies/")),
    url(r'^needs/in/constituency/(?P<slug>[-\w]+)/$', givefood.views.public_wfbn_constituency, name="public_wfbn_constituency"),
    url(r'^needs/in/constituency/(?P<slug>[-\w]+)/mp_photo_(?P<size>full|threefour).png$', givefood.views.public_wfbn_constituency_mp_photo, name="public_wfbn_constituency_mp_photo"),

    # Rickrolling
    url(r'^wp-login\.php$', RedirectView.as_view(url=RICK_ASTLEY)),

    # Old URL redirects
    url(r'^what-food-banks-need/$', RedirectView.as_view(url='/needs/')),
    url(r'^static/img/map-allloc\.png$', RedirectView.as_view(url="/static/img/map.png")),

    # API1
    url(r'^api/1/foodbanks/$', givefood.views.api_foodbanks, name="api_foodbanks"),
    url(r'^api/1/foodbanks/search/$', givefood.views.api_foodbank_search, name="api_foodbank_search"),
    url(r'^api/1/foodbank/(?P<slug>[-\w]+)/$', givefood.views.api_foodbank, name="api_foodbank"),
    url(r'^api/1/foodbank/$', givefood.views.api_foodbank_key, name="api_foodbank_key"),
    url(r'^api/1/needs/$', givefood.views.api_needs, name="api_needs"),
    url(r'^api/1/need/(?P<id>\b[0-9a-f]{8}\b)/$', givefood.views.api_need, name="api_need"),

    # Apps
    url(r'^api/2/', include('gfapi2.urls')),
    url(r'^admin/', include('gfadmin.urls')),

    # CSP & Auth
    url(r'^csp/', include('cspreports.urls')),
    url(r'^auth/', include('djangae.contrib.gauth.urls')),
)

if settings.DEBUG:
    urlpatterns += tuple(static(settings.STATIC_URL, view=serve, show_indexes=True))
