from itertools import chain
from django.shortcuts import get_object_or_404, render
from django.views.decorators.cache import never_cache
from django.db.models import Value, F
from django.urls import reverse

from django_earthdistance.models import EarthDistance, LlToEarth

from givefood.func import approx_rev_geocode, find_locations, geocode, miles
from givefood.models import Foodbank, FoodbankDonationPoint, FoodbankLocation


@never_cache
def index(request):
    return render(request, "app/index.html")


@never_cache
def search(request):

    lat_lng = request.GET.get("lat_lng", None)
    address = request.GET.get("address", None)
    approx_location = None

    # Geocode address if no lat_lng
    if address and not lat_lng:
        lat_lng = geocode(address)


    # Validate lat_lng
    try:
        lat = lat_lng.split(",")[0]
        lng = lat_lng.split(",")[1]
    except IndexError:
        return HttpResponseBadRequest()

    if not address:
        approx_location = approx_rev_geocode(lat_lng)

    if lat_lng:
        location_results = find_locations(lat_lng, 10)
        
        donationpoints = FoodbankDonationPoint.objects.filter(is_closed = False).annotate(
        distance=EarthDistance([
            LlToEarth([lat, lng]),
            LlToEarth([F('latitude'), F('longitude')])
        ])).annotate(type=Value("donationpoint")).order_by("distance")[:20]

        location_donationpoints = FoodbankLocation.objects.filter(is_closed = False, is_donation_point = True).annotate(
        distance=EarthDistance([
            LlToEarth([lat, lng]),
            LlToEarth([F('latitude'), F('longitude')])
        ])).annotate(type=Value("location")).order_by("distance")[:20]

        donationpoints = list(chain(donationpoints,location_donationpoints))
        donationpoints = sorted(donationpoints, key=lambda k: k.distance)[:20]

        for donationpoint in donationpoints:
            if donationpoint.type == "location":
                donationpoint.url = reverse("wfbn:foodbank_location", kwargs={"slug":donationpoint.foodbank_slug, "locslug":donationpoint.slug})
                donationpoint.photo_url = reverse("wfbn-generic:foodbank_location_photo", kwargs={"slug":donationpoint.foodbank_slug, "locslug":donationpoint.slug})
            if donationpoint.type == "donationpoint":
                donationpoint.url = reverse("wfbn:foodbank_donationpoint", kwargs={"slug":donationpoint.foodbank_slug, "dpslug":donationpoint.slug})
                donationpoint.photo_url = reverse("wfbn-generic:foodbank_donationpoint_photo", kwargs={"slug":donationpoint.foodbank_slug, "dpslug":donationpoint.slug})
            donationpoint.distance_mi = miles(donationpoint.distance)

    template_vars = {
        "address":address,
        "approx_location":approx_location,
        "lat_lng":lat_lng,
        "location_results":location_results,
    }

    return render(request, "app/search_results.html", template_vars)


@never_cache
def foodbank(request, slug):
    foodbank = get_object_or_404(Foodbank, slug=slug)
    donationpoints = FoodbankDonationPoint.objects.filter(foodbank=foodbank).order_by("name")
    locations = FoodbankLocation.objects.filter(foodbank=foodbank).order_by("name")
    template_vars = {
        "foodbank": foodbank,
        "donationpoints": donationpoints,
        "locations": locations,
    }
    return render(request, "app/foodbank.html", template_vars)


@never_cache
def location(request, slug, locslug):
    pass