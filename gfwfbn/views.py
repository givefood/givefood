from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponseRedirect, HttpResponse, HttpResponseForbidden
from django.template import RequestContext
from django.views.decorators.cache import cache_page
from django.template.defaultfilters import slugify

from google.appengine.api import urlfetch

from givefood.models import Foodbank, FoodbankLocation, ParliamentaryConstituency
from givefood.func import get_all_constituencies, get_all_foodbanks, get_all_locations, find_foodbanks, geocode, find_locations


def public_tt_old_data(request):

    recent = Foodbank.objects.filter(network = "Trussell Trust").order_by("-last_need")[:100]
    old = Foodbank.objects.filter(network = "Trussell Trust").order_by("last_need")[:100]

    template_vars = {
        "recent":recent,
        "old":old,
    }
    return render_to_response("tt-old-data.html", template_vars, context_instance=RequestContext(request))


@cache_page(60*10)
def public_what_food_banks_need(request):

    headless = request.GET.get("headless", False)
    where_from = request.GET.get("from", False)
    address = request.GET.get("address", "")
    lattlong = request.GET.get("lat_lng", "")

    map_locations = []
    location_results = []

    if where_from != "trusselltrust":
        foodbanks = get_all_foodbanks()
        locations = get_all_locations()

        for foodbank in foodbanks:
            map_locations.append(
                {
                    "latt_long":foodbank.latt_long,
                    "url":"/needs/at/%s/" % (foodbank.slug)
                }
            )

        for location in locations:
            map_locations.append(
                {
                    "latt_long":location.latt_long,
                    "url":"/needs/at/%s/%s/" % (location.foodbank_slug, location.slug)
                }
            )

        if address and not lattlong:
            lattlong = geocode(address)

        if lattlong:
            location_results = find_locations(lattlong, 10)

            for location in location_results:
                location_need = FoodbankChange.objects.filter(foodbank_name=location.get("foodbank_name"), published=True).latest("created")
                location["needs"] = location_need.change_text

    template_vars = {
        "headless":headless,
        "where_from":where_from,
        "address":address,
        "lattlong":lattlong,
        "map_locations":map_locations,
        "location_results":location_results,
    }
    return render_to_response("wfbnindex.html", template_vars, context_instance=RequestContext(request))


def public_what_food_banks_need_click(request, slug):

    foodbank = get_object_or_404(Foodbank, slug = slug)
    utm_querystring = "?utm_source=givefood_org_uk&utm_medium=search&utm_campaign=needs"
    redirect_url = "%s%s" % (
        foodbank.shopping_list_url,
        utm_querystring,
    )
    return redirect(redirect_url)


@cache_page(60*10)
def public_wfbn_foodbank(request, slug):

    foodbank = get_object_or_404(Foodbank, slug = slug)

    map_url = "https://maps.googleapis.com/maps/api/staticmap?center=%s&size=350x700&scale=2&maptype=roadmap&format=png&key=AIzaSyAyeRIfEOZenxIew6fSIQjl0AF0q1qIXoQ&markers=%s&markers=size:small|" % (foodbank.latt_long,foodbank.latt_long)
    for location in foodbank.locations():
        map_url += "|%s" % (location.latt_long)

    nearby_locations = find_locations(foodbank.latt_long, 10, True)

    template_vars = {
        "foodbank":foodbank,
        "nearby_locations":nearby_locations,
        "map_url":map_url,
    }

    return render_to_response("wfbnfoodbank.html", template_vars, context_instance=RequestContext(request))


@cache_page(60*30)
def public_wfbn_foodbank_map(request, slug):

    foodbank = get_object_or_404(Foodbank, slug = slug)

    result = urlfetch.fetch("https://maps.googleapis.com/maps/api/staticmap?center=%s&zoom=15&size=300x300&maptype=roadmap&format=png&visual_refresh=true&key=AIzaSyAyeRIfEOZenxIew6fSIQjl0AF0q1qIXoQ" % (foodbank.latt_long))
    return HttpResponse(result.content, content_type='image/png')


@cache_page(60*10)
def public_wfbn_foodbank_location(request, slug, locslug):

    foodbank = get_object_or_404(Foodbank, slug = slug)
    location = get_object_or_404(FoodbankLocation, slug = locslug, foodbank = foodbank)

    nearby_locations = find_locations(location.latt_long, 10, True)

    template_vars = {
        "foodbank":foodbank,
        "location":location,
        "nearby_locations":nearby_locations,
    }

    return render_to_response("foodbank_location.html", template_vars, context_instance=RequestContext(request))


@cache_page(60*30)
def public_wfbn_foodbank_location_map(request, slug, locslug):

    foodbank = get_object_or_404(Foodbank, slug = slug)
    location = get_object_or_404(FoodbankLocation, slug = locslug, foodbank = foodbank)

    result = urlfetch.fetch("https://maps.googleapis.com/maps/api/staticmap?center=%s&zoom=15&size=300x300&maptype=roadmap&format=png&visual_refresh=true&key=AIzaSyAyeRIfEOZenxIew6fSIQjl0AF0q1qIXoQ" % (location.latt_long))

    return HttpResponse(result.content, content_type='image/png')


@cache_page(60*5)
def public_wfbn_constituencies(request):

    postcode = request.GET.get("postcode", None)
    if postcode:
        admin_regions = admin_regions_from_postcode(postcode)
        parl_con = admin_regions.get("parliamentary_constituency", None)
        if parl_con:
            return HttpResponseRedirect(reverse("public_wfbn_constituency", kwargs={"slug":slugify(parl_con)}))

    constituencies = get_all_constituencies()

    template_vars = {
        "constituencies":constituencies,
    }

    return render_to_response("constituencies.html", template_vars, context_instance=RequestContext(request))


@cache_page(60*5)
def public_wfbn_constituency(request, slug):

    foodbanks = Foodbank.objects.filter(parliamentary_constituency_slug = slug)
    locations = FoodbankLocation.objects.filter(parliamentary_constituency_slug = slug)

    constituency_foodbanks = []

    for foodbank in foodbanks:
        constituency_foodbanks.append({
            "name":foodbank.name,
            "slug":foodbank.slug,
            "constituency_name":foodbank.parliamentary_constituency,
            "mp":foodbank.mp,
            "mp_party":foodbank.mp_party,
            "mp_parl_id":foodbank.mp_parl_id,
            "latt_long":foodbank.latt_long,
            "needs":foodbank.latest_need(),
            "url":"/needs/at/%s/" % (foodbank.slug)
        })

    for location in locations:
        constituency_foodbanks.append({
            "name":location.foodbank_name,
            "slug":location.foodbank_slug,
            "constituency_name":location.parliamentary_constituency,
            "mp":location.mp,
            "mp_party":location.mp_party,
            "mp_parl_id":location.mp_parl_id,
            "latt_long":location.latt_long,
            "needs":location.latest_need(),
            "url":"/needs/at/%s/%s/" % (location.foodbank_slug, location.slug)
        })

    #Dedupe
    constituency_locations = constituency_foodbanks
    constituency_foodbanks = {v['name']:v for v in constituency_foodbanks}.values()

    if not constituency_foodbanks:
        raise Http404

    constituency_name = constituency_foodbanks[0].get("constituency_name")
    mp = constituency_foodbanks[0].get("mp")
    mp_party = constituency_foodbanks[0].get("mp_party")
    mp_parl_id = constituency_foodbanks[0].get("mp_parl_id")

    template_vars = {
        "constituency_name":constituency_name,
        "constituency_slug":slugify(constituency_name),
        "mp":mp,
        "mp_party":mp_party,
        "mp_parl_id":mp_parl_id,
        "constituency_foodbanks":constituency_foodbanks,
        "constituency_locations":constituency_locations,
    }

    return render_to_response("constituency.html", template_vars, context_instance=RequestContext(request))


@cache_page(60*30)
def public_wfbn_constituency_mp_photo(request, slug, size):

    parl_con = get_object_or_404(ParliamentaryConstituency, slug=slug)
    result = urlfetch.fetch("https://storage.googleapis.com/mp_photos/%s/%s.png" % (size, parl_con.mp_parl_id))

    return HttpResponse(result.content, content_type='image/png')