from django.shortcuts import get_object_or_404, render
from django.views.decorators.cache import never_cache

from givefood.func import approx_rev_geocode, find_locations, geocode
from givefood.models import Foodbank, FoodbankChange, FoodbankDonationPoint, FoodbankLocation


@never_cache
def index(request):
    return render(request, "app/index.html")

def map(request):
    return render(request, "app/map.html")


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
def search_results(request):

    lat_lng = request.GET.get("lat_lng", None)
    address = request.GET.get("address", None)
    approx_location = None

    # Geocode address if no lat_lng
    if address and not lat_lng:
        lat_lng = geocode(address)
    if not address:
        approx_location = approx_rev_geocode(lat_lng)

    if lat_lng:
        location_results = find_locations(lat_lng, 10)

    template_vars = {
        "address":address,
        "approx_location":approx_location,
        "lat_lng":lat_lng,
        "location_results":location_results,
    }

    return render(request, "app/search_results.html", template_vars)