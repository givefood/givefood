from django.conf.urls import include
from django.conf.urls.i18n import i18n_patterns
from django.views.generic import RedirectView
from django.urls import path, re_path
from django.core.cache import cache
from django.db.utils import ProgrammingError, OperationalError


import givefood.views
from givefood.const.general import RICK_ASTLEY, FOODBANK_SUBPAGES

urlpatterns = []

# Old food bank slug redirects from database
def get_slug_redirects():
    """Get slug redirects from database with caching."""
    cache_key = 'slug_redirects_dict'
    redirects = cache.get(cache_key)
    
    if redirects is None:
        # Import here to avoid circular imports at module load time
        from givefood.models import SlugRedirect
        
        try:
            # Fetch all redirects from database
            slug_redirects = SlugRedirect.objects.all().values_list('old_slug', 'new_slug')
            redirects = dict(slug_redirects)
            
            # Cache for 1 hour (3600 seconds)
            cache.set(cache_key, redirects, 3600)
        except (ProgrammingError, OperationalError):
            # If table doesn't exist yet (e.g., during initial migration), return empty dict
            redirects = {}
    
    return redirects

old_foodbank_slugs = get_slug_redirects()

redirectors = {}
for old_slug, new_slug in old_foodbank_slugs.items():
    redirectors[("needs/at/%s/" % old_slug)] = ("/needs/at/%s/" % new_slug)
    for subpage in FOODBANK_SUBPAGES:
        redirectors["needs/at/%s/%s/" % (old_slug, subpage)] = "/needs/at/%s/%s/" % (new_slug, subpage)

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
    path("colophon/", givefood.views.colophon, name="colophon"),
    path("bot/", givefood.views.bot, name="bot"),
    path("frag/<slug:frag>/", givefood.views.frag, name="frag"),
    path("human/", givefood.views.human, name="human"),
    path("flag/", givefood.views.flag, name="flag"),

    # Donate
    path("donate/", givefood.views.donate, name="donate"),
    path("donate/managed/<slug:slug>-<slug:key>/", givefood.views.managed_donation, name="managed_donation"),
    path("donate/managed/<slug:slug>-<slug:key>/geo.json", givefood.views.managed_donation_geojson, name="managed_donation_geojson"),

    # Annual Reports
    path("annual-reports/", givefood.views.annual_report_index, name="annual_report_index"),
    re_path(r"^(?P<year>(2019|2020|2021|2022|2023|2024))/$", givefood.views.annual_report, name="annual_report"),

    # WFBN
    path("needs/", include('gfwfbn.urls.i18n', namespace="wfbn")),

    # Root
    path("<uuid:pk>/", givefood.views.uuid_redir, name="uuid_redir"),
    path("robots.txt", givefood.views.robotstxt, name="robotstxt"),
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
    path('appfe/', include('gfapp.urls', namespace="app")),
    path('auth/', include('gfauth.urls', namespace="auth")),
]