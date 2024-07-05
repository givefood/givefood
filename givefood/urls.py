import logging

from django.conf import settings
from django.conf.urls import include, url
from django.conf.urls.static import static
from django.views.generic import RedirectView

import givefood.views
from givefood.const.general import RICK_ASTLEY, OLD_FOODBANK_SLUGS, FOODBANK_SUBPAGES

import session_csrf
session_csrf.monkeypatch()

urlpatterns = [
    url(r'^_ah/', include('djangae.urls')),

    # PUBLIC
    url(r'^$', givefood.views.index, name="index"),

    url(r'^annual-reports/$', givefood.views.annual_report_index, name="annual_report_index"),
    url(r'^(?P<year>(2019|2020|2021|2022|2023))/$', givefood.views.annual_report, name="annual_report"),
    
    url(r'^register-foodbank/$', givefood.views.register_foodbank, name="register_foodbank"),

    url(r'^sitemap.xml$', givefood.views.sitemap, name="sitemap"),
    url(r'^sitemap_external.xml$', givefood.views.sitemap_external, name="sitemap_external"),
    
    url(r'^privacy/$', givefood.views.privacy, name="privacy"),
    url(r'^about-us/$', givefood.views.about_us, name="about_us"),
    url(r'^donate/$', givefood.views.donate, name="donate"),
    url(r'^frag/(?P<frag>[-\w]+)/$', givefood.views.frag, name="frag"),

    # KINDA PUBLIC
    url(r'^distill_webhook/$', givefood.views.distill_webhook, name="distill_webhook"),
    url(r'^proxy/(trusselltrust|ifan)/$', givefood.views.proxy, name="proxy"),

    # Rickrolling
    url(r'^wp-login\.php$', RedirectView.as_view(url=RICK_ASTLEY)),

    # Old URL redirects
    url(r'^what-food-banks-need/$', RedirectView.as_view(url='/needs/')),
    url(r'^static/img/map-allloc\.png$', RedirectView.as_view(url="/static/img/map.png")),
]

# Old Food Bank Redirects
for old_slug, new_slug in OLD_FOODBANK_SLUGS.items():
    urlpatterns.append(url(r'^needs/at/%s/$' % (old_slug), RedirectView.as_view(url='/needs/at/%s/' % new_slug)))
    for subpage in FOODBANK_SUBPAGES:
        urlpatterns.append(url(r'^needs/at/%s/%s/$' % (old_slug, subpage), RedirectView.as_view(url='/needs/at/%s/%s/' % (new_slug, subpage))))


# Apps
urlpatterns += [
    url(r'^needs/', include('gfwfbn.urls', namespace="wfbn")),
    url(r'^api/1/', include('gfapi1.urls')),
    url(r'^api/2/', include('gfapi2.urls', namespace="api2")),
    url(r'^api/3/', include('gfapi3.urls', namespace="api3")),
    url(r'^api/', include('gfapi2.urls')),
    url(r'^admin/', include('gfadmin.urls', namespace="admin")),
    url(r'^dashboard/', include('gfdash.urls', namespace="dash")),
    url(r'^offline/', include('gfoffline.urls', namespace="offline")),
    url(r'^write/', include('gfwrite.urls', namespace="write")),

] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)