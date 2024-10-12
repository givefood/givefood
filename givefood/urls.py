import logging

from django.conf import settings
from django.conf.urls import include, url
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

# Translated pages
urlpatterns += i18n_patterns(

    # Public
    path("", givefood.views.index, name="index"),
    path("register-foodbank/", givefood.views.register_foodbank, name="register_foodbank"),
    path("about-us/", givefood.views.about_us, name="about_us"),
    path("donate/", givefood.views.donate, name="donate"),
    path("frag/<slug:frag>/", givefood.views.frag, name="frag"),

    # Annual Reports
    path("annual-reports/", givefood.views.annual_report_index, name="annual_report_index"),
    re_path(r"^(?P<year>(2019|2020|2021|2022|2023))/$", givefood.views.annual_report, name="annual_report"),

    # WFBN
    path("needs/", include('gfwfbn.urls', namespace="wfbn")),

    prefix_default_language=False,
)
    
# Untranslated pages
urlpatterns += [
    re_path(r'^_ah/', include('djangae.urls')),

    path("sitemap.xml", givefood.views.sitemap, name="sitemap"),
    path("sitemap_external.xml", givefood.views.sitemap_external, name="sitemap_external"),
    path("privacy/", givefood.views.privacy, name="privacy"),

    # KINDA PUBLIC
    path("distill_webhook/", givefood.views.distill_webhook, name="distill_webhook"),
    re_path("proxy/(trusselltrust|ifan)/", givefood.views.proxy, name="proxy"),

    # Rickrolling
    path("wp-login.php", RedirectView.as_view(url=RICK_ASTLEY)),

    # Old URL redirects
    path("what-food-banks-need/", RedirectView.as_view(url='/needs/')),
    path("static/img/map-allloc.png", RedirectView.as_view(url="/static/img/map.png")),
]


# Untranslated apps
urlpatterns += [
    url(r'^api/1/', include('gfapi1.urls')),
    url(r'^api/2/', include('gfapi2.urls', namespace="api2")),
    url(r'^api/3/', include('gfapi3.urls', namespace="api3")),
    url(r'^api/', include('gfapi2.urls')),
    url(r'^admin/', include('gfadmin.urls', namespace="admin")),
    url(r'^dashboard/', include('gfdash.urls', namespace="dash")),
    url(r'^offline/', include('gfoffline.urls', namespace="offline")),
    url(r'^write/', include('gfwrite.urls', namespace="write")),
]