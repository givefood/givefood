import logging

from django.conf import settings
from django.conf.urls import include
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns
from django.views.generic import RedirectView
from django.urls import path, re_path


import givefood.views
from givefood.const.general import RICK_ASTLEY, OLD_FOODBANK_SLUGS, FOODBANK_SUBPAGES

urlpatterns = []

# Old food bank slug redirects
redirectors = {}
for old_slug, new_slug in OLD_FOODBANK_SLUGS.items():
    redirectors[("needs/at/%s/" % old_slug)] = ("/needs/at/%s/" % new_slug)
    for subpage in FOODBANK_SUBPAGES:
        redirectors["needs/at/%s/%s/" % (old_slug, subpage)] = "/needs/at/%s/%s/" % (new_slug, subpage)
for from_url, to_url in redirectors.copy().items():
    redirectors["cy/%s" % (from_url)] = "/cy%s" % (to_url)

redirect_patterns = []
for from_url, to_url in redirectors.items():
    redirect_patterns.append(path(from_url, RedirectView.as_view(url=to_url)))

urlpatterns += redirect_patterns

urlpatterns += [
    path("needs/", include('gfwfbn.urls.generic', namespace="wfbn-generic")),
]

# Translated pages
urlpatterns += i18n_patterns(

    # Public
    path("", givefood.views.index, name="index"),
    path("register-foodbank/", givefood.views.register_foodbank, name="register_foodbank"),
    path("about-us/", givefood.views.about_us, name="about_us"),
    path("frag/<slug:frag>/", givefood.views.frag, name="frag"),
    path("human/", givefood.views.human, name="human"),

    # Donate
    path("donate/", givefood.views.donate, name="donate"),
    path("donate/managed/<slug:slug>-<slug:key>/", givefood.views.managed_donation, name="managed_donation"),
    path("donate/managed/<slug:slug>-<slug:key>/geo.json", givefood.views.managed_donation_geojson, name="managed_donation_geojson"),

    # Annual Reports
    path("annual-reports/", givefood.views.annual_report_index, name="annual_report_index"),
    re_path(r"^(?P<year>(2019|2020|2021|2022|2023|2024))/$", givefood.views.annual_report, name="annual_report"),

    # WFBN
    path("needs/", include('gfwfbn.urls.i18n', namespace="wfbn")),

    # Sitemaps
    path("sitemap.xml", givefood.views.sitemap, name="sitemap"),

    prefix_default_language=False,
)
    
# Untranslated pages
urlpatterns += [

    # Warmup
    path("_ah/warmup", givefood.views.index, name="warmup"),
    path("_ah/start", givefood.views.index, name="start"),

    path("sitemap_external.xml", givefood.views.sitemap_external, name="sitemap_external"),
    path("privacy/", givefood.views.privacy, name="privacy"),

    # Rickrolling
    path("wp-login.php", RedirectView.as_view(url=RICK_ASTLEY)),

    # Old URL redirects
    path("what-food-banks-need/", RedirectView.as_view(url='/needs/')),
    path("static/img/map-allloc.png", RedirectView.as_view(url="/static/img/map.png")),
]


# Untranslated apps
urlpatterns += [
    path('api/1/', include('gfapi1.urls')),
    path('api/2/', include('gfapi2.urls', namespace="api2")),
    path('api/3/', include('gfapi3.urls', namespace="api3")),
    path('api/', include('gfapi2.urls')),
    path('admin/', include('gfadmin.urls', namespace="admin")),
    path('dashboard/', include('gfdash.urls', namespace="dash")),
    path('offline/', include('gfoffline.urls', namespace="offline")),
    path('write/', include('gfwrite.urls', namespace="write")),
]