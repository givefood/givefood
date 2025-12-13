from datetime import datetime, timedelta, date
import requests, json, tomllib, os
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_POST
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse, translate_url
from django.template.loader import render_to_string
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse, Http404
from django.db.models import Sum
from django.utils.timesince import timesince
from django.utils.translation import gettext_lazy as _, gettext
from django.contrib.humanize.templatetags.humanize import intcomma
from session_csrf import anonymous_csrf
from django.conf import settings

from givefood.models import Foodbank, FoodbankChange, FoodbankChangeLine, FoodbankDonationPoint, FoodbankHit, FoodbankLocation, Order, OrderGroup, ParliamentaryConstituency, Place
from givefood.forms import FoodbankRegistrationForm, FlagForm
from givefood.func import get_cred, validate_turnstile
from givefood.func import send_email
from givefood.const.general import BOT_USER_AGENT, SITE_DOMAIN, PLACES_PER_SITEMAP
from givefood.const.cache_times import (
    SECONDS_IN_DAY,
    SECONDS_IN_HOUR,
    SECONDS_IN_TWO_MINUTES,
    SECONDS_IN_WEEK
)
from givefood.settings import LANGUAGES


# Country configuration for country-specific pages
COUNTRY_MAPPING = {
    'scotland': 'Scotland',
    'england': 'England',
    'wales': 'Wales',
    'northern-ireland': 'Northern Ireland',
}

# Map center coordinates and zoom levels for each country
# Chosen to center the map on the geographical center of each country
COUNTRY_MAP_CONFIG = {
    'Scotland': {
        'lat': 57.7,
        'lng': -4,
        'zoom': 7
    },
    'England': {
        'lat': 53,
        'lng': -1.8,
        'zoom': 7
    },
    'Wales': {
        'lat': 52.3,
        'lng': -3.7,
        'zoom': 8
    },
    'Northern Ireland': {
        'lat': 54.6,
        'lng': -6.5,
        'zoom': 8
    },
}

# Example postcodes and towns for country search placeholders
COUNTRY_PLACEHOLDERS = {
    'Scotland': _('e.g. EH12 5PJ or Glasgow'),
    'England': _('e.g. HA9 0WS or Manchester'),
    'Wales': _('e.g. CF10 1NS or Cardiff'),
    'Northern Ireland': _('e.g. BT12 6LW or Belfast'),
}


@cache_page(SECONDS_IN_HOUR)
def index(request):
    """
    Give Food homepage, with stats and logos
    """

    logos = [
        {
            "name":"Trussell",
            "slug":"trussell",
            "url":"https://www.trussell.org.uk",
            "format":"svg",
        },
        {
            "name":"The Times",
            "slug":"thetimes",
            "url":"https://www.thetimes.co.uk",
            "format":"png",
        },
        {
            "name":"NHS",
            "slug":"nhs",
            "url":"https://www.nhs.uk",
            "format":"svg",
        },
        {
            "name":"BBC",
            "slug":"bbc",
            "url":"https://www.bbc.co.uk",
            "format":"svg",
        },
        {
            "name":"Scottish Government Riaghaltas na h-Alba",
            "slug":"scottishgov",
            "url":"https://www.gov.scot",
            "format":"svg",
        },
        {
            "name":"Consumer Data Research Centre",
            "slug":"cdrc",
            "url":"https://www.cdrc.ac.uk",
            "format":"png",
        },
        {
            "name":"Reach plc",
            "slug":"reach",
            "url":"https://www.reachplc.com",
            "format":"svg",
        },
        {
            "name":"Age UK",
            "slug":"ageuk",
            "url":"https://www.ageuk.org.uk",
            "format":"svg",
        },
        {
            "name":"Independent Food Aid Network",
            "slug":"ifan",
            "url":"https://www.foodaidnetwork.org.uk",
            "format":"svg",
        },
        {
            "name":"Channel 4",
            "slug":"channel4",
            "url":"https://www.channel4.com",
            "format":"svg",
        },
        {
            "name":"Welsh Government",
            "slug":"welshgov",
            "url":"https://www.gov.wales",
            "format":"svg",
        },
        {
            "name":"Foreign, Commonwealth & Development Office",
            "slug":"fcdo",
            "url":"https://www.gov.uk/government/organisations/foreign-commonwealth-development-office",
            "format":"svg",
        },
        {
            "name":"Mars",
            "slug":"mars",
            "url":"https://www.mars.com/en-gb",
            "format":"svg",
        },
        {
            "name":"Citizens Advice",
            "slug":"ca",
            "url":"https://www.citizensadvice.org.uk/",
            "format":"svg",
        },
        {
            "name":"National Council for the Training of Journalists",
            "slug":"nctj",
            "url":"https://www.nctj.com/",
            "format":"png",
        },
    ]

    stats = {
        "foodbanks":Foodbank.objects.count() + Foodbank.objects.exclude(delivery_address = "").count() + FoodbankLocation.objects.count(),
        "donationpoints":FoodbankDonationPoint.objects.count() + Foodbank.objects.exclude(address_is_administrative = True).count() + Foodbank.objects.exclude(delivery_address = "").count() + FoodbankLocation.objects.filter(is_donation_point = True).count(),
        "items":FoodbankChangeLine.objects.count(),
        "meals":int(Order.objects.aggregate(Sum("calories"))["calories__sum"]/500),
    }

    # Recently updated food banks
    exclude_change_text = ["Unknown", "Facebook", "Nothing"]
    recently_updated = (
        FoodbankChange.objects
        .filter(published=True)
        .exclude(change_text__in=exclude_change_text)
        .only('foodbank_name')
        .order_by("-created")[:10]
    )

    # Most viewed food banks
    most_viewed = (
        Foodbank.objects
        .filter(
            foodbankhit__day__gte=date.today() - timedelta(days=7),
            foodbankhit__day__lte=date.today()
        )
        .annotate(total_hits=Sum('foodbankhit__hits'))
        .order_by('-total_hits')[:10]
        .only('name', 'slug')
    )


    map_config = {
        "geojson":reverse("wfbn:geojson"),
        "lat": 55.4,
        "lng": -4,
        "zoom": 6,
        "location_marker": False,
    }
    map_config = json.dumps(map_config)
    gmap_key = get_cred("gmap_key")

    template_vars = {
        "recently_updated":recently_updated,
        "most_viewed":most_viewed,
        "gmap_key":gmap_key,
        "map_config":map_config,
        "logos":logos,
        "stats":stats,
        "is_home":True,
    }
    return render(request, "public/index.html", template_vars)


@cache_page(SECONDS_IN_HOUR)
def country(request, country_slug):
    """
    Country-specific page with food banks filtered by country
    """

    # Get country name from slug
    country_name = COUNTRY_MAPPING.get(country_slug)
    if not country_name:
        raise Http404("Country not found")

    # Recently updated food banks for this country (deduplicated)
    exclude_change_text = ["Unknown", "Facebook", "Nothing"]
    recent_changes = (
        FoodbankChange.objects
        .filter(published=True, foodbank__country=country_name)
        .exclude(change_text__in=exclude_change_text)
        .only('foodbank_name')
        .order_by("-created")[:50]  # Fetch more to ensure we have 10 unique
    )

    # Deduplicate by foodbank_name
    seen_foodbanks = set()
    recently_updated = []
    for change in recent_changes:
        if change.foodbank_name not in seen_foodbanks:
            seen_foodbanks.add(change.foodbank_name)
            recently_updated.append(change)
            if len(recently_updated) >= 10:
                break

    # Most viewed food banks for this country
    most_viewed = (
        Foodbank.objects
        .filter(
            foodbankhit__day__gte=date.today() - timedelta(days=7),
            foodbankhit__day__lte=date.today(),
            country=country_name
        )
        .annotate(total_hits=Sum('foodbankhit__hits'))
        .order_by('-total_hits')[:10]
        .only('name', 'slug')
    )

    # Map configuration
    map_settings = COUNTRY_MAP_CONFIG[country_name]
    map_config = {
        "geojson": reverse(
            "country_geojson",
            kwargs={"country_slug": country_slug}
        ),
        "lat": map_settings['lat'],
        "lng": map_settings['lng'],
        "zoom": map_settings['zoom'],
        "location_marker": False,
    }
    map_config = json.dumps(map_config)
    gmap_key = get_cred("gmap_key")

    template_vars = {
        "country_name": country_name,
        "country_slug": country_slug,
        "placeholder": COUNTRY_PLACEHOLDERS[country_name],
        "recently_updated": recently_updated,
        "most_viewed": most_viewed,
        "gmap_key": gmap_key,
        "map_config": map_config,
        "is_country_page": True,
    }
    return render(request, "public/country.html", template_vars)


@cache_page(SECONDS_IN_HOUR)
def country_geojson(request, country_slug):
    """
    GeoJSON endpoint for country-specific food banks
    """

    country_name = COUNTRY_MAPPING.get(country_slug)
    if not country_name:
        raise Http404("Country not found")

    # Get all food banks, locations, and donation points for this country
    foodbanks = Foodbank.objects.filter(
        country=country_name,
        is_closed=False
    ).only(
        'slug', 'name', 'alt_name', 'address', 'postcode',
        'lat_lng', 'delivery_address', 'delivery_lat_lng'
    )
    locations = FoodbankLocation.objects.filter(
        country=country_name,
        is_closed=False
    ).only(
        'name', 'foodbank_name', 'foodbank_slug', 'slug',
        'address', 'postcode', 'lat_lng', 'boundary_geojson'
    )
    donationpoints = FoodbankDonationPoint.objects.filter(
        country=country_name,
        is_closed=False
    ).only(
        'name', 'foodbank_name', 'foodbank_slug', 'slug',
        'address', 'postcode', 'lat_lng'
    )

    features = []
    decimal_places = 4

    # Add food banks
    for foodbank in foodbanks:
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [
                    round(foodbank.long(), decimal_places),
                    round(foodbank.latt(), decimal_places)
                ],
            },
            "properties": {
                "type": "f",
                "name": foodbank.full_name(),
                "address": foodbank.full_address(),
                "url": reverse(
                    "wfbn:foodbank",
                    kwargs={"slug": foodbank.slug}
                ),
            }
        })

        # Add delivery address if it exists (check both fields)
        if foodbank.delivery_address and foodbank.delivery_lat_lng:
            delivery_lat = foodbank.delivery_lat_lng.split(",")[0]
            delivery_lng = foodbank.delivery_lat_lng.split(",")[1]
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [
                        round(float(delivery_lng), decimal_places),
                        round(float(delivery_lat), decimal_places)
                    ],
                },
                "properties": {
                    "type": "f",
                    "name": "%s Delivery Address" % (foodbank.full_name()),
                    "address": foodbank.delivery_address,
                    "url": reverse(
                        "wfbn:foodbank",
                        kwargs={"slug": foodbank.slug}
                    ),
                }
            })

    # Add locations
    for location in locations:
        lat = location.lat_lng.split(",")[0]
        lng = location.lat_lng.split(",")[1]
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [
                    round(float(lng), decimal_places),
                    round(float(lat), decimal_places)
                ],
            },
            "properties": {
                "type": "l",
                "name": location.name,
                "foodbank": location.foodbank_name,
                "address": location.full_address(),
                "url": reverse(
                    "wfbn:foodbank_location",
                    kwargs={
                        "slug": location.foodbank_slug,
                        "locslug": location.slug
                    }
                ),
            }
        })

    # Add donation points
    for dp in donationpoints:
        lat = dp.lat_lng.split(",")[0]
        lng = dp.lat_lng.split(",")[1]
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [
                    round(float(lng), decimal_places),
                    round(float(lat), decimal_places)
                ],
            },
            "properties": {
                "type": "d",
                "name": dp.name,
                "foodbank": dp.foodbank_name,
                "address": dp.full_address(),
                "url": reverse(
                    "wfbn:foodbank_donationpoint",
                    kwargs={
                        "slug": dp.foodbank_slug,
                        "dpslug": dp.slug
                    }
                ),
            }
        })

    response_dict = {
        "type": "FeatureCollection",
        "features": features
    }

    return JsonResponse(response_dict)


@cache_page(SECONDS_IN_WEEK)
def annual_report_index(request):
    """
    Annual report homepage, with links to each year's report
    """
    return render(request, "public/ar/index.html")


@cache_page(SECONDS_IN_WEEK)
def annual_report(request, year):
    """
    Annual report page, with report content
    """
    return render(request, "public/ar/%s.html" % (year))


@anonymous_csrf
def register_foodbank(request):
    """
    Food bank registration form
    """
    
    done = request.GET.get("thanks", False)

    if request.POST:
        form = FoodbankRegistrationForm(request.POST)

        turnstile_is_valid = validate_turnstile(request.POST.get("cf-turnstile-response"))

        if form.is_valid() and turnstile_is_valid:
            email_body = render_to_string("public/registration_email.txt",{"form":request.POST.items()})
            send_email(
                to = "mail@givefood.org.uk",
                subject = "New Food Bank Registration - %s" % (request.POST.get("name")),
                body = email_body,
            )
            completed_url = "%s%s" % (reverse("register_foodbank"),"?thanks=1")
            return redirect(completed_url)
    else:
        form = FoodbankRegistrationForm()

    template_vars = {
        "form":form,
        "done":done,
    }
    return render(request, "public/register_foodbank.html", template_vars)


@cache_page(SECONDS_IN_WEEK)
def donate(request):
    """
    Donate page
    """
    return render(request, "public/donate.html")


@cache_page(SECONDS_IN_HOUR)
def managed_donation(request, slug, key):
    """
    Managed donation page
    """

    order_group = get_object_or_404(OrderGroup, slug=slug, key=key, public=True)

    items = 0
    weight = 0
    calories = 0
    cost = 0

    for order in order_group.orders():
        items += order.no_items
        weight += order.weight_kg_pkg()
        calories += order.calories
        cost += order.cost

    map_config = {
        "geojson":reverse("managed_donation_geojson", kwargs={"slug":slug, "key":key}),
        "lat": 55.4,
        "lng": -4,
        "zoom": 6,
        "location_marker": False,
    }
    map_config = json.dumps(map_config)

    template_vars = {
        "order_group":order_group,
        "items":items,
        "weight":weight,
        "calories":calories,
        "cost":cost/100,
        "meals":int(calories/500),
        "map_config":map_config,
    }
    return render(request, "public/managed_donation.html", template_vars)


@cache_page(SECONDS_IN_HOUR)
def managed_donation_geojson(request, slug, key):

    order_group = get_object_or_404(OrderGroup, slug=slug, key=key, public=True)

    features = []
    for order in order_group.orders():
        feature = {
            "type":"Feature",
            "geometry":{
                "type":"Point",
                "coordinates":[order.foodbank.long(), order.foodbank.latt()],
            },
            "properties":{
                "type":"f",
                "name":order.foodbank.name,
                "address":order.foodbank.address,
                "postcode":order.foodbank.postcode,
                "no_items":order.no_items,
                "weight":order.weight_kg_pkg(),
                "calories":order.calories,
                "cost":order.cost/100,
                "url":reverse("wfbn:foodbank", kwargs={"slug":order.foodbank.slug}),
            }
        }
        features.append(feature)

    response_dict = {
            "type": "FeatureCollection",
            "features": features
    }

    return JsonResponse(response_dict)


def managed_donation_items(request, slug, key):
    """
    Managed donation items list
    """

    order_group = get_object_or_404(OrderGroup, slug=slug, key=key, public=True)
    orders = order_group.orders().prefetch_related('orderline_set__item')

    template_vars = {
        "order_group":order_group,
        "orders":orders,
    }
    return render(request, "public/managed_donation_items.html", template_vars)


@cache_page(SECONDS_IN_WEEK)
def about_us(request):
    """
    About us page
    """
    return render(request, "public/about_us.html")


@cache_page(SECONDS_IN_WEEK)
def api(request):
    """
    API doc index
    """
    return render(request, "public/api.html")


def uuid_redir(request, pk):
    """
    Redirect to the correct page for a given UUID by checking models in order.
    """
    foodbank = Foodbank.objects.filter(uuid=pk).first()
    if foodbank:
        return redirect("wfbn:foodbank", slug=foodbank.slug)

    location = FoodbankLocation.objects.filter(uuid=pk).first()
    if location:
        return redirect(
            "wfbn:foodbank_location",
            slug=location.foodbank_slug,
            locslug=location.slug
        )

    donation_point = FoodbankDonationPoint.objects.filter(uuid=pk).first()
    if donation_point:
        return redirect(
            "wfbn:foodbank_donationpoint",
            slug=donation_point.foodbank_slug,
            dpslug=donation_point.slug
        )

    raise Http404(f"Object with UUID {pk} not found.")


@cache_page(SECONDS_IN_WEEK)
def sitemap(request):
    """
    XML sitemap for search engines
    """

    url_names = [
        "index",
        "about_us",
        "donate",
        "annual_report_index",
        "privacy",
    ]

    # Country slugs for sitemap
    country_slugs = ['scotland', 'england', 'wales', 'northern-ireland']

    foodbanks = Foodbank.objects.all().exclude(is_closed=True).only(
        'slug',
        'days_between_needs',
        'no_locations',
        'no_donation_points',
        'rss_url',
        'charity_name',
        'facebook_page',
        'twitter_handle'
    )
    constituencies = ParliamentaryConstituency.objects.all().only('slug')
    locations = (
        FoodbankLocation.objects.all()
        .exclude(is_closed=True)
        .only('foodbank_slug', 'slug')
    )
    donationpoints = (
        FoodbankDonationPoint.objects.all()
        .exclude(is_closed=True)
        .only('foodbank_slug', 'slug')
    )

    template_vars = {
        "domain": SITE_DOMAIN,
        "url_names": url_names,
        "country_slugs": country_slugs,
        "foodbanks": foodbanks,
        "constituencies": constituencies,
        "locations": locations,
        "donationpoints": donationpoints,
    }
    return render(
        request,
        "public/sitemap.xml",
        template_vars,
        content_type='text/xml'
    )


@cache_page(SECONDS_IN_WEEK)
def robotstxt(request):
    """
    /robots.txt
    """
    
    get_location_url = reverse("wfbn:get_location")
    flag_url = reverse("flag")
    sitemap_url = reverse("sitemap")
    sitemap_places_index_url = reverse("sitemap_places_index")

    disallowed_urls = []
    sitemap_urls = []
    for language in LANGUAGES:
        lang_code = language[0]
        disallowed_urls.append(translate_url(get_location_url, lang_code))
        disallowed_urls.append(translate_url(flag_url, lang_code))
        sitemap_urls.append(translate_url(sitemap_url, lang_code))
        sitemap_urls.append(translate_url(sitemap_places_index_url, lang_code))

    template_vars = {
        "domain":SITE_DOMAIN,
        "disallowed_urls":disallowed_urls,
        "sitemap_urls":sitemap_urls,
    }

    return render(request, "public/robots.txt", template_vars, content_type='text/plain')


@cache_page(SECONDS_IN_DAY)
def manifest(request):
    """
    Web app manifest
    """

    start_url = SITE_DOMAIN
    lang = request.LANGUAGE_CODE

    manifest_content = {
        "name" : "Give Food",
        "short_name" : "Give Food",
        "description" : gettext("Use Give Food's tool to find what food banks near you are requesting to have donated"),
        "start_url" : start_url,
        "display" : "minimal-ui",
        "lang" : lang,
        "icons": [
            {
                "src": "/static/img/favicon.svg",
                "sizes": "48x48 72x72 96x96 128x128 256x256 512x512",
                "type": "image/svg+xml",
                "purpose": "any"
            }
        ],
        "screenshots": [
            {
                "src": "/static/img/manifestscreens/index.png",
                "type": "image/png",
                "sizes": "1402x2356"
            },
            {
                "src": "/static/img/manifestscreens/search.png",
                "type": "image/png",
                "sizes": "1402x2356"
            },
            {
                "src": "/static/img/manifestscreens/foodbank.png",
                "type": "image/png",
                "sizes": "1402x2356"
            }
        ],
        "prefer_related_applications": True,
        "related_applications": [
            {
                "platform": "play",
                "url": "https://play.google.com/store/apps/details?id=uk.org.givefood.android",
                "id": "uk.org.givefood.android"
            }
        ]
    }

    return HttpResponse(json.dumps(manifest_content), content_type="application/json")


@cache_page(SECONDS_IN_WEEK)
def llmstxt(request):
    """
    /llms.txt - LLM-friendly site index
    """
    
    # Calculate foodbank and donation point counts same as homepage
    foodbanks_count = Foodbank.objects.count() + Foodbank.objects.exclude(delivery_address = "").count() + FoodbankLocation.objects.count()
    donationpoints_count = FoodbankDonationPoint.objects.count() + Foodbank.objects.exclude(address_is_administrative = True).count() + Foodbank.objects.exclude(delivery_address = "").count() + FoodbankLocation.objects.filter(is_donation_point = True).count()
    
    template_vars = {
        "domain":SITE_DOMAIN,
        "foodbanks_count": foodbanks_count,
        "donationpoints_count": donationpoints_count,
    }
    
    return render(request, "public/llms.txt", template_vars, content_type='text/plain; charset=utf-8')


@cache_page(SECONDS_IN_WEEK)
def sitemap_external(request):
    """
    XML sitemap for external links
    """

    foodbanks = Foodbank.objects.all().exclude(is_closed=True).only('url', 'shopping_list_url', 'rss_url')

    template_vars = {
        "domain":SITE_DOMAIN,
        "foodbanks":foodbanks,
    }
    return render(request, "public/sitemap_external.xml", template_vars, content_type='text/xml')


@cache_page(SECONDS_IN_WEEK)
def sitemap_places_index(request):
    """
    Sitemap index for places - splits 75k places into multiple sitemaps
    """
    total_places = Place.objects.count()
    num_sitemaps = (total_places + PLACES_PER_SITEMAP - 1) // PLACES_PER_SITEMAP  # ceiling division
    
    template_vars = {
        "domain": SITE_DOMAIN,
        "sitemap_pages": range(1, num_sitemaps + 1),
    }
    return render(request, "public/sitemap_places_index.xml", template_vars, content_type='text/xml')


@cache_page(SECONDS_IN_WEEK)
def sitemap_places(request, page=1):
    """
    Sitemap for places - paginated to handle 75k places
    """
    offset = (page - 1) * PLACES_PER_SITEMAP
    
    places = Place.objects.all().only('county_slug', 'name_slug').order_by('id')[offset:offset + PLACES_PER_SITEMAP]
    
    template_vars = {
        "domain": SITE_DOMAIN,
        "places": places,
    }
    return render(request, "public/sitemap_places.xml", template_vars, content_type='text/xml')


@cache_page(SECONDS_IN_WEEK)
def privacy(request):
    """
    Privacy policy
    """
    return render(request, "public/privacy.html")


@cache_page(SECONDS_IN_WEEK)
def colophon(request):
    """
    Colophon
    """
    pyproject_url = "https://raw.githubusercontent.com/givefood/givefood/refs/heads/main/pyproject.toml"
    pyproject_text = requests.get(pyproject_url).content
    pyproject_data = tomllib.loads(pyproject_text.decode("utf-8"))
    
    # Extract dependency names from pyproject.toml
    requirement_names = []
    for dep in pyproject_data.get("project", {}).get("dependencies", []):
        # Parse dependency string to get just the package name
        # Handle formats like "django==5.2.7", "django-session-csrf", "sentry-sdk[django]"
        dep_name = dep.split("==")[0].split(">=")[0].split("<=")[0].split("[")[0].strip()
        requirement_names.append(dep_name)
    requirement_names.sort()

    template_vars = {
        "requirements":requirement_names,
    }
    return render(request, "public/colophon.html", template_vars)


@cache_page(SECONDS_IN_WEEK)
def bot(request):
    """
    Bot user agent info page
    """
    template_vars = {
        "BOT_USER_AGENT": BOT_USER_AGENT,
    }
    return render(request, "public/bot.html", template_vars)


@cache_page(SECONDS_IN_DAY)
def apps(request):
    return render(request, "public/apps.html")


@cache_page(SECONDS_IN_TWO_MINUTES)
def frag(request, frag):
    """
    Fragments for client side includes
    """

    allowed_frags = [
        "last-updated",
        "need-hits",
    ]
    if frag not in allowed_frags:
        raise Http404()

    # last-updated"
    if frag == "last-updated":
        timesince_text = timesince(Foodbank.objects.latest("modified").modified)
        if timesince_text == "0 %s" % (_("minutes")):
            frag_text = _("Under a minute ago")
        else:
            frag_text = "%s %s" % (timesince_text, _("ago"))

    # need-hits
    if frag == "need-hits":
        number_hits = FoodbankHit.objects.filter(day__gte=datetime.now() - timedelta(days=7)).aggregate(Sum('hits'))["hits__sum"]
        frag_text = intcomma(number_hits, False)
    
    if not frag_text:
        return HttpResponseForbidden()

    return HttpResponse(frag_text)


@require_POST
def human(request):
    """
    Human check
    """
    post_vars = request.POST.dict()

    target = post_vars.get("target")
    if not target:
        return HttpResponseForbidden()
    post_vars.pop("target")
    action = post_vars.get("action")
    if not action:
        return HttpResponseForbidden()
    post_vars.pop("action")

    tempate_vars = {
        "headless":True,
        "target":target,
        "action":action,
        "post_vars":post_vars,
    }
    return render(request, "public/human.html", tempate_vars)


@cache_page(SECONDS_IN_DAY)
def flag(request):
    """
    Flag a page
    """
    done = request.GET.get("thanks", False)

    if request.POST:
        form = FlagForm(request.POST)

        turnstile_is_valid = validate_turnstile(request.POST.get("cf-turnstile-response"))

        if form.is_valid() and turnstile_is_valid:

            fields = request.POST.copy()
            fields.pop("csrfmiddlewaretoken", None)
            fields.pop("cf-turnstile-response", None)

            email_body = render_to_string("public/flag_email.txt",{"form":fields.items()})
            send_email(
                to = "mail@givefood.org.uk",
                subject = "Give Food - Flagged Page",
                body = email_body,
            )
            completed_url = "%s%s" % (reverse("flag"),"?thanks=1")
            return redirect(completed_url)
    else:
        form = FlagForm()

    template_vars = {
        "is_flag_page":True,
        "form":form,
        "done":done,
    }
    return render(request, "public/flag.html", template_vars)


def slug_redirect(request, old_slug, new_slug, subpage=None):
    """
    Redirect old food bank slugs to new ones while preserving language prefix.
    
    This view is used for i18n-aware redirects that maintain the current language
    prefix in the URL. For example, /ar/needs/at/durham/ redirects to 
    /ar/needs/at/county-durham/ (preserving the 'ar' language code).
    """
    from django.utils.translation import get_language
    
    # Build the new URL path
    if subpage:
        new_path = f"/needs/at/{new_slug}/{subpage}/"
    else:
        new_path = f"/needs/at/{new_slug}/"
    
    # Get current language and prefix the URL if not English (default)
    current_language = get_language()
    if current_language and current_language != 'en':
        new_path = f"/{current_language}{new_path}"
    
    return redirect(new_path, permanent=True)


@cache_page(SECONDS_IN_HOUR)
def service_worker(request):
    """
    Dynamically generates the Firebase messaging service worker JavaScript file.
    This file must be served from the root of the website at /firebase-messaging-sw.js
    as Firebase SDK expects this specific filename.
    The Firebase config is embedded directly in the service worker.
    """
    from givefood.func import get_cred
    
    # Get Firebase config
    api_key = get_cred("firebase_api_key") or ""
    auth_domain = get_cred("firebase_auth_domain") or ""
    project_id = get_cred("firebase_project_id") or ""
    storage_bucket = get_cred("firebase_storage_bucket") or ""
    messaging_sender_id = get_cred("firebase_messaging_sender_id") or ""
    app_id = get_cred("firebase_app_id") or ""
    
    sw_content = f'''// Give Food Service Worker for Web Push Notifications
// This file is dynamically generated by Django with Firebase config embedded

importScripts('https://www.gstatic.com/firebasejs/9.22.0/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/9.22.0/firebase-messaging-compat.js');

// Initialize Firebase with embedded config
firebase.initializeApp({{
    apiKey: "{api_key}",
    authDomain: "{auth_domain}",
    projectId: "{project_id}",
    storageBucket: "{storage_bucket}",
    messagingSenderId: "{messaging_sender_id}",
    appId: "{app_id}"
}});

const messaging = firebase.messaging();

// Handle background messages
messaging.onBackgroundMessage(function(payload) {{
    console.log('[Service Worker] Received background message:', payload);
    
    const notificationTitle = payload.notification?.title || payload.data?.title || 'Give Food';
    const notificationOptions = {{
        body: payload.notification?.body || payload.data?.body || '',
        icon: '/static/img/logo.svg',
        badge: '/static/img/logo.svg',
        data: {{
            foodbank_slug: payload.data?.foodbank_slug,
            click_action: payload.data?.click_action || payload.fcmOptions?.link
        }}
    }};
    
    return self.registration.showNotification(notificationTitle, notificationOptions);
}});

// Handle notification click
self.addEventListener('notificationclick', function(event) {{
    event.notification.close();
    
    // Get the URL from the notification data
    let url = '/needs/';
    if (event.notification.data && event.notification.data.foodbank_slug) {{
        url = '/needs/at/' + event.notification.data.foodbank_slug + '/';
    }}
    if (event.notification.data && event.notification.data.click_action) {{
        url = event.notification.data.click_action;
    }}

    event.waitUntil(
        clients.matchAll({{ type: 'window', includeUncontrolled: true }}).then(function(clientList) {{
            // If there's an existing window, focus it
            for (let i = 0; i < clientList.length; i++) {{
                const client = clientList[i];
                if ('focus' in client) {{
                    return client.focus().then(function(focusedClient) {{
                        if ('navigate' in focusedClient) {{
                            return focusedClient.navigate(url);
                        }}
                    }});
                }}
            }}
            // Otherwise open a new window
            if (clients.openWindow) {{
                return clients.openWindow(url);
            }}
        }})
    );
}});
'''
    
    return HttpResponse(sw_content, content_type='application/javascript')