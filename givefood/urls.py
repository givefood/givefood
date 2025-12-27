from django.conf.urls import include
from django.conf.urls.i18n import i18n_patterns
from django.views.generic import RedirectView
from django.urls import path, re_path


import givefood.views
from givefood.func import get_slug_redirects
from givefood.const.general import RICK_ASTLEY, FOODBANK_SUBPAGES


def generate_slug_redirect_patterns():
    """Generate URL redirect patterns for old food bank slugs."""
    from functools import partial
    
    old_foodbank_slugs = get_slug_redirects()
    
    redirect_patterns = []
    for old_slug, new_slug in old_foodbank_slugs.items():
        # Main foodbank page redirect - use custom view that preserves language
        redirect_patterns.append(
            path(
                f"needs/at/{old_slug}/",
                partial(givefood.views.slug_redirect, old_slug=old_slug, new_slug=new_slug),
                name=f"redirect_{old_slug}"
            )
        )
        # Subpage redirects
        for subpage in FOODBANK_SUBPAGES:
            redirect_patterns.append(
                path(
                    f"needs/at/{old_slug}/{subpage}/",
                    partial(givefood.views.slug_redirect, old_slug=old_slug, new_slug=new_slug, subpage=subpage),
                    name=f"redirect_{old_slug}_{subpage}"
                )
            )
    
    return redirect_patterns


urlpatterns = []

urlpatterns += [
    path("needs/", include('gfwfbn.urls.generic', namespace="wfbn-generic")),
]

# Translated pages
urlpatterns += i18n_patterns(

    # Old food bank slug redirects - must be inside i18n_patterns to work for all languages
    *generate_slug_redirect_patterns(),

    # Public
    path("", givefood.views.index, name="index"),
    path("register-foodbank/", givefood.views.register_foodbank, name="register_foodbank"),
    path("about-us/", givefood.views.about_us, name="about_us"),
    path("colophon/", givefood.views.colophon, name="colophon"),
    path("bot/", givefood.views.bot, name="bot"),
    path("apps/", givefood.views.apps, name="apps"),
    path("frag/<slug:frag>/", givefood.views.frag, name="frag"),
    path("human/", givefood.views.human, name="human"),
    path("flag/", givefood.views.flag, name="flag"),
    
    # Country pages - must be before generic slug patterns
    re_path(r"^(?P<country_slug>(scotland|england|wales|northern-ireland))/$", givefood.views.country, name="country"),
    re_path(r"^(?P<country_slug>(scotland|england|wales|northern-ireland))/geo\.json$", givefood.views.country_geojson, name="country_geojson"),

    # Donate
    path("donate/", givefood.views.donate, name="donate"),
    path("donate/managed/<slug:slug>-<slug:key>/", givefood.views.managed_donation, name="managed_donation"),
    path("donate/managed/<slug:slug>-<slug:key>/geo.json", givefood.views.managed_donation_geojson, name="managed_donation_geojson"),
    path("donate/managed/<slug:slug>-<slug:key>/items/", givefood.views.managed_donation_items, name="managed_donation_items"),

    # Annual Reports
    path("annual-reports/", givefood.views.annual_report_index, name="annual_report_index"),
    re_path(r"^(?P<year>(2019|2020|2021|2022|2023|2024|2025))/$", givefood.views.annual_report, name="annual_report"),

    # WFBN
    path("needs/", include('gfwfbn.urls.i18n', namespace="wfbn")),

    # Root
    path("<uuid:pk>/", givefood.views.uuid_redir, name="uuid_redir"),
    path("robots.txt", givefood.views.robotstxt, name="robotstxt"),
    path("manifest.json", givefood.views.manifest, name="manifest"),
    path("sitemap.xml", givefood.views.sitemap, name="sitemap"),
    path("sitemap_places_index.xml", givefood.views.sitemap_places_index, name="sitemap_places_index"),
    path("sitemap_places.xml", givefood.views.sitemap_places, name="sitemap_places"),
    path("sitemap_places_<int:page>.xml", givefood.views.sitemap_places, name="sitemap_places_page"),

    prefix_default_language=False,
)
    
# Untranslated pages
urlpatterns += [

    path("llms.txt", givefood.views.llmstxt, name="llmstxt"),
    path("sitemap_external.xml", givefood.views.sitemap_external, name="sitemap_external"),
    path("privacy/", givefood.views.privacy, name="privacy"),
    path("firebase-messaging-sw.js", givefood.views.service_worker, name="service_worker"),
    path("sw.js", givefood.views.vapid_service_worker, name="vapid_service_worker"),

    # Rickrolling
    path("wp-login.php", RedirectView.as_view(url=RICK_ASTLEY)),

    # Old URL redirects
    path("what-food-banks-need/", RedirectView.as_view(url='/needs/')),
]


# Untranslated apps
urlpatterns += [
    path('api/1/', include('gfapi1.urls')),
    path('api/2/', include('gfapi2.urls', namespace="api2")),
    path('api/3/', include('gfapi3.urls', namespace="api3")),
    path('api/', include('gfapi2.urls')),
    path('admin/', include('gfadmin.urls', namespace="admin")),
    path('dashboard/', include('gfdash.urls', namespace="dash")),
    path('dumps/', include('gfdumps.urls', namespace="dumps")),
    path('offline/', include('gfoffline.urls', namespace="offline")),
    path('write/', include('gfwrite.urls', namespace="write")),
    path('auth/', include('gfauth.urls', namespace="auth")),
]