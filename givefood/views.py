from datetime import datetime, timedelta, date
import requests, json, tomllib
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_POST
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse, translate_url
from django.template.loader import render_to_string
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse, Http404
from django.db.models import Sum
from django.utils.timesince import timesince
from django.utils.translation import gettext_lazy as _
from django.contrib.humanize.templatetags.humanize import intcomma
from session_csrf import anonymous_csrf

from givefood.const.topplaces import TOP_PLACES
from givefood.models import Changelog, Foodbank, FoodbankChange, FoodbankChangeLine, FoodbankDonationPoint, FoodbankHit, FoodbankLocation, Order, OrderGroup, ParliamentaryConstituency, Place
from givefood.forms import FoodbankRegistrationForm, FlagForm
from givefood.func import get_cred, validate_turnstile
from givefood.func import send_email
from givefood.const.general import BOT_USER_AGENT, SITE_DOMAIN
from givefood.const.cache_times import SECONDS_IN_DAY, SECONDS_IN_HOUR, SECONDS_IN_TWO_MINUTES, SECONDS_IN_WEEK
from givefood.settings import LANGUAGES


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
    locations = FoodbankLocation.objects.all().exclude(is_closed=True).only('foodbank_slug', 'slug')
    donationpoints = FoodbankDonationPoint.objects.all().exclude(is_closed=True).only('foodbank_slug', 'slug')
    top_places = TOP_PLACES

    template_vars = {
        "domain":SITE_DOMAIN,
        "url_names":url_names,
        "foodbanks":foodbanks,
        "constituencies":constituencies,
        "locations":locations,
        "donationpoints":donationpoints,
        "top_places":top_places,
    }
    return render(request, "public/sitemap.xml", template_vars, content_type='text/xml')


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
        disallowed_urls.append(translate_url(get_location_url, language[0]))
        disallowed_urls.append(translate_url(flag_url, language[0]))
        sitemap_urls.append(translate_url(sitemap_url, language[0]))
    
    # Add places sitemap index (not translated)
    sitemap_urls.append(sitemap_places_index_url)

    template_vars = {
        "domain":SITE_DOMAIN,
        "disallowed_urls":disallowed_urls,
        "sitemap_urls":sitemap_urls,
    }

    return render(request, "public/robots.txt", template_vars, content_type='text/plain')


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
    places_per_sitemap = 50000
    total_places = Place.objects.count()
    num_sitemaps = (total_places + places_per_sitemap - 1) // places_per_sitemap  # ceiling division
    
    template_vars = {
        "domain": SITE_DOMAIN,
        "num_sitemaps": num_sitemaps,
    }
    return render(request, "public/sitemap_places_index.xml", template_vars, content_type='text/xml')


@cache_page(SECONDS_IN_WEEK)
def sitemap_places(request, page=1):
    """
    Sitemap for places - paginated to handle 75k places
    """
    places_per_sitemap = 50000
    offset = (page - 1) * places_per_sitemap
    
    places = Place.objects.all().only('county_slug', 'name_slug').order_by('id')[offset:offset + places_per_sitemap]
    
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

    changelog = Changelog.objects.all().order_by("-date")
    template_vars = {
        "changelog":changelog,
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