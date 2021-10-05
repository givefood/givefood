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
    url(r'^(?P<year>(2019|2020))/$', givefood.views.public_annual_report, name="public_annual_report"),
    url(r'^register-foodbank/$', givefood.views.public_reg_foodbank, name="public_reg_foodbank"),
    url(r'^sitemap.xml$', givefood.views.public_sitemap, name="public_sitemap"),
    url(r'^privacy/$', givefood.views.public_privacy, name="public_privacy"),

    # KINDA PUBLIC
    url(r'^generate-(?P<year>(2019|2020|2021))/$', givefood.views.public_gen_annual_report, name="public_gen_annual_report"),
    url(r'^productimage/$', givefood.views.public_product_image, name="public_product_image"),
    url(r'^distill_webhook/$', givefood.views.distill_webhook, name="distill_webhook"),
    url(r'^proxy/(trusselltrust|ifan)/$', givefood.views.proxy, name="proxy"),

    # Rickrolling
    url(r'^wp-login\.php$', RedirectView.as_view(url=RICK_ASTLEY)),

    # Old URL redirects
    url(r'^what-food-banks-need/$', RedirectView.as_view(url='/needs/')),
    url(r'^static/img/map-allloc\.png$', RedirectView.as_view(url="/static/img/map.png")),

    # Apps
    url(r'^needs/', include('gfwfbn.urls', namespace="wfbn", app_name="gfwfbn")),
    url(r'^api/1/', include('gfapi1.urls')),
    url(r'^api/2/', include('gfapi2.urls')),
    url(r'^api/', include('gfapi2.urls')),
    url(r'^admin/', include('gfadmin.urls')),
    url(r'^dashboard/', include('gfdash.urls', namespace="dash", app_name="gfdash")),
    url(r'^offline/', include('gfoffline.urls', namespace="offline", app_name="gfoffline")),

    # CSP & Auth
    url(r'^csp/', include('cspreports.urls')),
    url(r'^auth/', include('djangae.contrib.gauth.urls')),
)

if settings.DEBUG:
    urlpatterns += tuple(static(settings.STATIC_URL, view=serve, show_indexes=True))
