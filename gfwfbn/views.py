import json, requests, datetime

from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseRedirect, HttpResponse, HttpResponseForbidden, HttpResponseNotFound, JsonResponse, HttpResponseBadRequest, Http404
from django.db import IntegrityError
from django.template.loader import render_to_string
from django.views.decorators.cache import cache_page, never_cache
from django.template.defaultfilters import slugify
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.core.validators import validate_email
from django import forms
from django.utils.translation import gettext

from givefood.const.general import SITE_DOMAIN

from givefood.models import CharityYear, Foodbank, FoodbankDonationPoint, FoodbankHit, FoodbankLocation, ParliamentaryConstituency, FoodbankChange, FoodbankSubscriber, FoodbankArticle, Place
from givefood.func import geocode, find_locations, find_donationpoints, admin_regions_from_postcode, get_cred, get_screenshot, is_uk, photo_from_place_id, send_email, get_all_constituencies, validate_turnstile
from givefood.const.cache_times import SECONDS_IN_HOUR, SECONDS_IN_DAY, SECONDS_IN_WEEK
from django.db.models import Sum


@cache_page(SECONDS_IN_HOUR)
def index(request, lat_lng=None, page_title=None):
    """
    The What Food Banks Need index page
    """ 

    # Handle old misspelt URL
    if request.GET.get("lattlong", None):
        return redirect("%s?lat_lng=%s" % (reverse("wfbn:index"), request.GET.get("lattlong")), permanent=True)

    # All the vars we'll need
    address = request.GET.get("address", "")
    if not lat_lng:
        lat_lng = request.GET.get("lat_lng", "")

    lat_lng_is_uk = True
    lat = lng = approx_address = locations = donationpoints = None

    # Geocode address if no lat_lng
    if address and not lat_lng:
        lat_lng = geocode(address)

    if lat_lng:
        # Validate lat_lng
        try:
            lat = lat_lng.split(",")[0]
            lng = lat_lng.split(",")[1]
        except IndexError:
            return HttpResponseBadRequest()
        
        # Check if lat_lng is in UK
        lat_lng_is_uk = is_uk(lat_lng)

        if lat_lng_is_uk:
            locations = find_locations(lat_lng, 20)
            donationpoints = find_donationpoints(lat_lng, 20)
    else:
        return redirect(reverse("index"), permanent=True)


    map_config = {
        "geojson":reverse("wfbn:geojson"),
        "lat":lat_lng.split(",")[0],
        "lng":lat_lng.split(",")[1],
        "zoom":13,
        "location_marker":True
    }
    map_config = json.dumps(map_config)
    

    # Need the Google Maps API key too
    gmap_key = get_cred("gmap_key")

    template_vars = {
        "page_title":page_title,
        "address":address,
        "lat":lat,
        "lng":lng,
        "gmap_key":gmap_key,
        "locations":locations,
        "donationpoints":donationpoints,
        "is_uk":lat_lng_is_uk,
        "map_config":map_config,
    }
    return render(request, "wfbn/index.html", template_vars)


@cache_page(SECONDS_IN_DAY)
def rss(request, slug=None):
    """
    RSS feed for site-wide updates or a specific food bank
    If slug is provided, returns feed for that food bank only.
    Otherwise, returns site-wide feed.
    """ 

    foodbank = None
    if slug:
        foodbank = get_object_or_404(Foodbank, slug = slug)

    # Get needs - filter by foodbank if slug provided
    needs_query = FoodbankChange.objects.filter(published = True).exclude(change_text = "Nothing").exclude(change_text = "Facebook").exclude(change_text = "Unknown").select_related('foodbank')
    if foodbank:
        needs_query = needs_query.filter(foodbank = foodbank)
    needs = needs_query.order_by("-created")[:10]

    # Get news - filter by foodbank if slug provided
    news_query = FoodbankArticle.objects.all()
    if foodbank:
        news_query = news_query.filter(foodbank = foodbank)
    news = news_query.order_by("-published_date")[:10]

    # Put them all together
    items = []
    for need in needs:
        title = "%s %s %s" % (need.no_items(), gettext("items requested at"), need.foodbank.full_name())
        url = "%s%s#need-%s" % (SITE_DOMAIN, reverse("wfbn:foodbank", args=[need.foodbank.slug]), need.need_id)
        items.append({
            "title": title,
            "url": url,
            "date": need.created,
            "description": need.get_change_text(),
        })
    for newsitem in news:
        items.append({
            "title":newsitem.title,
            "url":newsitem.url,
            "date":newsitem.published_date,
        })

    # Sort all the items by date
    items = sorted(items, key=lambda d: d['date'], reverse=True) 

    template_vars = {
        "SITE_DOMAIN":SITE_DOMAIN,
        "items":items,
    }
    if foodbank:
        template_vars["foodbank"] = foodbank

    return render(request, "wfbn/rss.xml", template_vars, content_type='text/xml')


@never_cache
def get_location(request):
    """
    Handle non-javascript location requests
    """

    response = requests.get("https://freeipapi.com/api/json/%s" % (request.META.get("HTTP_CF_CONNECTING_IP", None)))
    if response.status_code != 200:
        return HttpResponseBadRequest()
    response_json = response.json()
    url = reverse("wfbn:index")
    redirect_url = "%s?lat_lng=%s,%s" % (url, response_json["latitude"], response_json["longitude"])
    return redirect(redirect_url)


@cache_page(SECONDS_IN_WEEK)
def geojson(request, slug = None, parlcon_slug = None, locslug = None):
    """
    GeoJSON for everything, a food bank, a parliamentary constituency, or a specific location
    """

    # All items
    all_items = not slug and not parlcon_slug and not locslug

    # Number of decimal places for coordinates
    if all_items:
        decimal_places = 4
    else:
        decimal_places = 6

    # Handle bad fb slug
    if slug:
        foodbank = get_object_or_404(Foodbank, slug = slug)

    # Handle location-specific request
    if locslug:
        # Query for the specific location with optimized field selection
        locations = FoodbankLocation.objects.filter(slug = locslug, foodbank__slug = slug).only('name', 'foodbank_name', 'foodbank_slug', 'slug', 'address', 'postcode', 'lat_lng', 'boundary_geojson')
        # Ensure the location exists (404 if not found)
        if not locations.exists():
            raise Http404("Location not found")
        # Only return the location, not the foodbank or donation points
        foodbanks = Foodbank.objects.none()
        donationpoints = FoodbankDonationPoint.objects.none()
    elif slug:
        foodbanks = Foodbank.objects.filter(slug = slug).only('slug', 'name', 'alt_name', 'address', 'postcode', 'lat_lng', 'delivery_address', 'delivery_lat_lng')
        locations = FoodbankLocation.objects.filter(foodbank__slug = slug).only('name', 'foodbank_name', 'foodbank_slug', 'slug', 'address', 'postcode', 'lat_lng', 'boundary_geojson')
        donationpoints = FoodbankDonationPoint.objects.filter(foodbank__slug = slug).only('name', 'foodbank_name', 'foodbank_slug', 'slug', 'address', 'postcode', 'lat_lng')
    elif parlcon_slug:
        foodbanks = Foodbank.objects.filter(parliamentary_constituency_slug = parlcon_slug, is_closed=False).only('slug', 'name', 'alt_name', 'address', 'postcode', 'lat_lng', 'delivery_address', 'delivery_lat_lng')
        locations = FoodbankLocation.objects.filter(parliamentary_constituency_slug = parlcon_slug, is_closed=False).only('name', 'foodbank_name', 'foodbank_slug', 'slug', 'address', 'postcode', 'lat_lng', 'boundary_geojson')
        donationpoints = FoodbankDonationPoint.objects.filter(parliamentary_constituency_slug = parlcon_slug, is_closed=False).only('name', 'foodbank_name', 'foodbank_slug', 'slug', 'address', 'postcode', 'lat_lng')
    else:
        foodbanks = Foodbank.objects.filter(is_closed=False).only('slug', 'name', 'alt_name', 'address', 'postcode', 'lat_lng', 'delivery_address', 'delivery_lat_lng')
        locations = FoodbankLocation.objects.filter(is_closed=False).only('name', 'foodbank_name', 'foodbank_slug', 'slug', 'address', 'postcode', 'lat_lng', 'boundary_geojson')
        donationpoints = FoodbankDonationPoint.objects.filter(is_closed=False).only('name', 'foodbank_name', 'foodbank_slug', 'slug', 'address', 'postcode', 'lat_lng')

    features = []

    # Parlcon outline
    if parlcon_slug:
        parlcon = get_object_or_404(ParliamentaryConstituency, slug = parlcon_slug)
        boundary = parlcon.boundary_geojson_dict()
        boundary["properties"]["type"] = "b"
        features.append(boundary)

    for foodbank in foodbanks:
        features.append({
            "type":"Feature",
            "geometry":{
                "type":"Point",
                "coordinates":[round(foodbank.long(), decimal_places), round(foodbank.latt(), decimal_places)],
            },
            "properties":{
                "type":"f",
                "name":foodbank.full_name(),
                "address":foodbank.full_address(),
                "url":reverse("wfbn:foodbank", kwargs={"slug":foodbank.slug}),
            }
        })
        if foodbank.delivery_address:
            features.append({
                "type":"Feature",
                "geometry":{
                    "type":"Point",
                    "coordinates":[round(foodbank.delivery_long(), decimal_places), round(foodbank.delivery_latt(), decimal_places)],
                },
                "properties":{
                    "type":"f",
                    "name":"%s Delivery Address" % (foodbank.full_name()),
                    "address":foodbank.delivery_address,
                    "url":reverse("wfbn:foodbank", kwargs={"slug":foodbank.slug}),
                }
            })
    
    for location in locations:
        if location.boundary_geojson and not all_items:
            boundary = location.boundary_geojson_dict()
            boundary["properties"] = {
                "type":"lb",
                "name":location.name,
                "foodbank":location.foodbank_name,
                "url":reverse("wfbn:foodbank_location", kwargs={"slug":location.foodbank_slug, "locslug":location.slug}),
            }
            features.append(boundary)
        else:
            features.append({
                "type":"Feature",
                "geometry":{
                    "type":"Point",
                    "coordinates":[round(location.long(), decimal_places), round(location.latt(), decimal_places)],
                },
                "properties":{
                    "type":"l",
                    "name":location.name,
                    "foodbank":location.foodbank_name,
                    "address":location.full_address(),
                    "url":reverse("wfbn:foodbank_location", kwargs={"slug":location.foodbank_slug, "locslug":location.slug}),
                }
            })

    for donationpoint in donationpoints:
        features.append({
            "type":"Feature",
            "geometry":{
                "type":"Point",
                "coordinates":[round(donationpoint.long(), decimal_places), round(donationpoint.latt(), decimal_places)],
            },
            "properties":{
                "type":"d",
                "name":donationpoint.name,
                "foodbank":donationpoint.foodbank_name,
                "address":donationpoint.full_address(),
                "url":reverse("wfbn:foodbank_donationpoint", kwargs={"slug":donationpoint.foodbank_slug, "dpslug":donationpoint.slug}),
            }
        })

    # Remove address if all items (for download size)
    if all_items:
        for feature in features:
            feature["properties"].pop("address", None)

    response_dict = {
            "type": "FeatureCollection",
            "features": features
    }

    return JsonResponse(response_dict)


@cache_page(SECONDS_IN_DAY)
def place(request, county, place):
    """
    Place page
    """

    try:
        place = Place.objects.filter(county_slug=county, name_slug=place).first()
        if not place:
            raise Http404("Place not found")
    except Place.DoesNotExist:
        raise Http404("Place not found")
    lat_lng = place.lat_lng
    county = place.uniauth if place.uniauth else place.adcounty
    title = "%s, %s" % (place.name, county)

    return index(request, lat_lng = lat_lng, page_title = title)
    
    

@cache_page(SECONDS_IN_DAY)
def foodbank(request, slug):
    """
    Food bank index
    """

    foodbank = get_object_or_404(Foodbank.objects.select_related("latest_need"), slug = slug)

    change_text = foodbank.latest_need.change_text

    if change_text == "Unknown" or change_text == "Nothing":
        template = "noneed"
    else:
        template = "withneed"

    map_config = {
        "geojson":reverse("wfbn:foodbank_geojson", kwargs={"slug":foodbank.slug}),
        "max_zoom":14,
    }
    map_config = json.dumps(map_config)

    template_vars = {
        "section":"foodbank",
        "foodbank":foodbank,
        "map_config":map_config,
    }

    return render(request, "wfbn/foodbank/index_%s.html" % (template), template_vars)


# Constants for map sizes
MAP_SIZE_SMALL = 300
MAP_SIZE_MEDIUM = 600
MAP_SIZE_LARGE = 1080

# Map size to dimensions and scale configuration
MAP_SIZE_CONFIG = {
    MAP_SIZE_SMALL: ("150x150", 2),    # Small: 150x150 at 2x scale (retina)
    MAP_SIZE_MEDIUM: ("600x400", 1),   # Medium: 600x400 at 1x scale (default)
    MAP_SIZE_LARGE: ("540x360", 2),    # Large: 540x360 at 2x scale (retina)
}


def get_map_dimensions_and_scale(size):
    """
    Helper function to get map dimensions and scale for a given size parameter.
    
    This function converts the logical size parameter into Google Maps Static API
    dimensions and scale values. Higher scale values provide retina-quality images.
    
    Args:
        size (int): The size parameter, one of MAP_SIZE_SMALL (300), MAP_SIZE_MEDIUM (600), 
                    or MAP_SIZE_LARGE (1080)
    
    Returns:
        tuple: (dimensions_string, scale_factor) or (None, None) if invalid size
        
    Examples:
        >>> get_map_dimensions_and_scale(300)
        ('150x150', 2)
        >>> get_map_dimensions_and_scale(600)
        ('600x400', 1)
        >>> get_map_dimensions_and_scale(1080)
        ('540x360', 2)
        >>> get_map_dimensions_and_scale(999)
        (None, None)
    """
    return MAP_SIZE_CONFIG.get(size, (None, None))


@cache_page(SECONDS_IN_WEEK)
def foodbank_map(request, slug, size=600):
    """
    Food bank map PNG
    """
    dimensions, scale = get_map_dimensions_and_scale(size)
    if dimensions is None:
        return HttpResponseBadRequest()

    foodbank = get_object_or_404(Foodbank, slug = slug)

    # Main markers
    main_markers = "icon:https://www.givefood.org.uk/static/img/mapmarkers/32/red.png|%s" % foodbank.lat_lng
    if foodbank.delivery_address:
        main_markers += "|%s" % (foodbank.delivery_lat_lng)

    # Location markers
    loc_markers = ""
    if foodbank.no_locations != 0:
        loc_markers += "icon:https://www.givefood.org.uk/static/img/mapmarkers/16/yellow.png|"
        for location in foodbank.locations():
            loc_markers += "%s|" % (location.lat_lng)

    # Donation point markers
    dp_markers = ""
    if foodbank.no_donation_points != 0:
        dp_markers += "icon:https://www.givefood.org.uk/static/img/mapmarkers/16/blue.png|"
        for donationpoint in foodbank.donation_points():
            dp_markers += "%s|" % (donationpoint.lat_lng)

    base_url = "https://maps.googleapis.com/maps/api/staticmap"
    params = [
        ("center", foodbank.lat_lng),
        ("size", dimensions),
        ("scale", scale),
        ("maptype", "roadmap"),
        ("format", "png"),
        ("language", request.LANGUAGE_CODE),
        ("key", get_cred("gmap_static_key")),
    ]
    if dp_markers:
        params.append(("markers", dp_markers))
    if loc_markers:
        params.append(("markers", loc_markers))
    params.append(("markers", main_markers))

    response = requests.get(base_url, params=params)
    if response.status_code != 200:
        return HttpResponseBadRequest()

    return HttpResponse(response.content, content_type="image/png")


@cache_page(SECONDS_IN_WEEK)
def foodbank_photo(request, slug):
    """
    Food bank photo JPEG
    """

    size = request.GET.get("size", 1080)
    foodbank = get_object_or_404(Foodbank, slug = slug)

    if not foodbank.place_has_photo:
        return HttpResponseNotFound()
    
    photo = photo_from_place_id(foodbank.place_id, size)
    
    return HttpResponse(photo, content_type='image/jpeg')


@cache_page(SECONDS_IN_WEEK)
def foodbank_screenshot(request, slug, page_name):
    """
    Food bank webpage screenshot
    """

    foodbank = get_object_or_404(Foodbank, slug = slug)

    if page_name == "homepage":
        url = foodbank.url
    if page_name == "shoppinglist":
        url = foodbank.shopping_list_url
    if page_name == "donationpoints":
        url = foodbank.donation_points_url
    if page_name == "contacts":
        url = foodbank.contacts_url
    if page_name == "locations":
        url = foodbank.locations_url

    if not url:
        return HttpResponseNotFound()
    
    photo = get_screenshot(url)

    if photo:
        return HttpResponse(photo, content_type='image/png')
    else:
        return HttpResponseNotFound()


@cache_page(SECONDS_IN_DAY)
def foodbank_locations(request,slug):
    """
    Food bank locations index
    """

    foodbank = get_object_or_404(Foodbank, slug = slug)
    if foodbank.no_locations == 0:
        return HttpResponseNotFound()

    map_config = {
        "geojson":reverse("wfbn:foodbank_geojson", kwargs={"slug":foodbank.slug}),
    }
    map_config = json.dumps(map_config)

    template_vars = {
        "section":"locations",
        "foodbank":foodbank,
        "map_config":map_config,
    }

    return render(request, "wfbn/foodbank/locations.html", template_vars)


@cache_page(SECONDS_IN_DAY)
def foodbank_donationpoints(request,slug):
    """
    Food bank donation points index
    """

    foodbank = get_object_or_404(Foodbank, slug = slug)
    if foodbank.no_donation_points == 0:
        return HttpResponseNotFound()
    
    map_config = {
        "geojson":reverse("wfbn:foodbank_geojson", kwargs={"slug":foodbank.slug}),
    }
    map_config = json.dumps(map_config)

    template_vars = {
        "section":"donationpoints",
        "foodbank":foodbank,
        "map_config":map_config,
    }

    return render(request, "wfbn/foodbank/donationpoints.html", template_vars)

@cache_page(SECONDS_IN_DAY)
def foodbank_news(request,slug):
    """
    Food bank news
    """

    foodbank = get_object_or_404(Foodbank, slug = slug)
    if not foodbank.rss_url:
        return HttpResponseNotFound()

    template_vars = {
        "section":"news",
        "foodbank":foodbank,
    }

    return render(request, "wfbn/foodbank/news.html", template_vars)


@cache_page(SECONDS_IN_DAY)
def foodbank_charity(request, slug):
    """
    Food bank charity information
    """

    foodbank = get_object_or_404(Foodbank, slug = slug)
    charity_years = CharityYear.objects.filter(foodbank = foodbank).order_by("-date")

    if not foodbank.charity_name:
        return HttpResponseNotFound()

    template_vars = {
        "section":"charity",
        "foodbank":foodbank,
        "charity_years":charity_years,
    }

    return render(request, "wfbn/foodbank/charity.html", template_vars)


@cache_page(SECONDS_IN_DAY)
def foodbank_socialmedia(request, slug):
    """
    Food bank social media links
    """

    foodbank = get_object_or_404(Foodbank, slug = slug)
    # TODO: check if fb has social media

    template_vars = {
        "section":"socialmedia",
        "foodbank":foodbank,
    }

    return render(request, "wfbn/foodbank/socialmedia.html", template_vars)


@cache_page(SECONDS_IN_WEEK)
def foodbank_nearby(request, slug):
    """
    Food bank nearby list
    """

    foodbank = get_object_or_404(Foodbank, slug = slug)
    nearby_locations = find_locations(foodbank.lat_lng, 20, True)

    map_config = {
        "geojson":reverse("wfbn:geojson"),
        "lat": foodbank.latt(),
        "lng": foodbank.long(),
        "zoom": 12,
        "location_marker": False,
    }
    map_config = json.dumps(map_config)

    template_vars = {
        "section":"nearby",
        "foodbank":foodbank,
        "nearby":nearby_locations,
        "map_config":map_config,
    }

    return render(request, "wfbn/foodbank/nearby.html", template_vars)


@cache_page(SECONDS_IN_WEEK)
def foodbank_subscribe(request, slug):
    """
    Food bank subscribe page
    """

    foodbank = get_object_or_404(Foodbank, slug = slug)
    email = request.GET.get("email", None)
    turnstilefail = request.GET.get("email", None)

    template_vars = {
        "section":"subscribe",
        "foodbank":foodbank,
        "email":email,
        "turnstilefail":turnstilefail,
    }

    return render(request, "wfbn/foodbank/subscribe.html", template_vars)


@cache_page(SECONDS_IN_WEEK)
def foodbank_subscribe_sample(request, slug):
    """
    Food bank subscribe sample email
    Used in an iframe in the subscribe page
    """

    foodbank = get_object_or_404(Foodbank, slug = slug)

    template_vars = {
        "need":foodbank.latest_need,
        "is_sample":True,
    }

    return render(request, "wfbn/emails/notification.html", template_vars)


@cache_page(SECONDS_IN_DAY)
def foodbank_location(request, slug, locslug):
    """
    Food bank individual location
    """

    foodbank = get_object_or_404(Foodbank.objects.select_related("latest_need"), slug = slug)
    location = get_object_or_404(FoodbankLocation, slug = locslug, foodbank = foodbank)

    change_text = foodbank.latest_need.change_text
    if change_text == "Unknown" or change_text == "Nothing":
        template = "noneed"
    else:
        template = "withneed"

    map_config = {
        "geojson":reverse("wfbn:foodbank_geojson", kwargs={"slug":foodbank.slug}),
        "lat": location.latt(),
        "lng": location.long(),
        "zoom": 15,
        "location_marker": False,
    }
    if location.boundary_geojson:
        map_config["zoom"] = 12
    map_config = json.dumps(map_config)

    template_vars = {
        "section":"locations",
        "foodbank":foodbank,
        "location":location,
        "map_config":map_config,
    }

    return render(request, "wfbn/foodbank/location_%s.html" % (template), template_vars)


@cache_page(SECONDS_IN_WEEK)
def foodbank_location_map(request, slug, locslug, size=600):
    """
    Food bank location map PNG
    """
    dimensions, scale = get_map_dimensions_and_scale(size)
    if dimensions is None:
        return HttpResponseBadRequest()

    foodbank = get_object_or_404(Foodbank, slug = slug)
    location = get_object_or_404(FoodbankLocation, slug = locslug, foodbank = foodbank)

    # Use zoom 12 if boundary exists to show more area, otherwise zoom 15
    zoom = 11 if location.boundary_geojson else 15
    
    base_url = "https://maps.googleapis.com/maps/api/staticmap"
    params = [
        ("center", location.lat_lng),
        ("zoom", zoom),
        ("size", dimensions),
        ("scale", scale),
        ("maptype", "roadmap"),
        ("format", "png"),
        ("visual_refresh", "true"),
        ("language", request.LANGUAGE_CODE),
        ("key", get_cred("gmap_static_key")),
    ]

    # Add boundary polygon if it exists
    if location.boundary_geojson:
        try:
            boundary_dict = location.boundary_geojson_dict()
            if boundary_dict and boundary_dict.get("geometry") and boundary_dict["geometry"].get("type") == "Polygon":
                coordinates = boundary_dict["geometry"]["coordinates"][0]  # Get outer ring
                
                # Simplify coordinates to reduce URL length
                # 1. Reduce precision to 4 decimal places (~11m accuracy)
                # 2. Downsample if too many points (keep every Nth point)
                max_points = 100  # Limit to avoid URL length issues
                if len(coordinates) > max_points:
                    # Calculate step to reduce points, ensure step is at least 2
                    step = max(2, len(coordinates) // max_points)
                    simplified = [coordinates[i] for i in range(0, len(coordinates), step)]
                    # Ensure last point is included (closes the polygon)
                    if coordinates[-1] not in simplified:
                        simplified.append(coordinates[-1])
                    coordinates = simplified
                
                # Format: fillcolor:0xf7a72333 (orange with ~20% opacity) | color:0xf7a723ff (orange border) | weight:1
                path_param = "fillcolor:0xf7a72333|color:0xf7a723ff|weight:1"
                for coord in coordinates:
                    # GeoJSON uses [lng, lat] order, Google Maps uses lat,lng
                    # Round to 4 decimal places to reduce URL length
                    path_param += "|%.4f,%.4f" % (coord[1], coord[0])
                params.append(("path", path_param))
        except (KeyError, IndexError, json.JSONDecodeError):
            # If there's any error parsing the boundary, just continue without it
            pass

    response = requests.get(base_url, params=params)

    return HttpResponse(response.content, content_type='image/png')


@cache_page(SECONDS_IN_WEEK)
def foodbank_location_photo(request, slug, locslug):
    """
    Food bank location photo JPEG
    """

    size = request.GET.get("size", 1080)
    foodbank = get_object_or_404(Foodbank, slug = slug)
    location = get_object_or_404(FoodbankLocation, slug = locslug, foodbank = foodbank)

    if not location.place_has_photo:
        return HttpResponseNotFound()
    
    photo = photo_from_place_id(location.place_id, size)
    
    return HttpResponse(photo, content_type='image/jpeg')


@cache_page(SECONDS_IN_DAY)
def foodbank_donationpoint(request, slug, dpslug):
    """
    Food bank donation point
    """

    foodbank = get_object_or_404(Foodbank.objects.select_related("latest_need"), slug = slug)
    donationpoint = get_object_or_404(FoodbankDonationPoint, slug = dpslug, foodbank = foodbank)

    change_text = foodbank.latest_need.change_text
    if change_text == "Unknown" or change_text == "Nothing" or change_text == "Facebook":
        has_need = False
    else:
        has_need = True
    
    map_config = {
        "geojson":reverse("wfbn:foodbank_geojson", kwargs={"slug":foodbank.slug}),
        "lat": donationpoint.latt(),
        "lng": donationpoint.long(),
        "zoom": 15,
        "location_marker": False,
    }
    map_config = json.dumps(map_config)

    template_vars = {
        "section":"donationpoints",
        "foodbank":foodbank,
        "has_need":has_need,
        "donationpoint":donationpoint,
        "map_config":map_config,
    }

    response = render(request, "wfbn/foodbank/donationpoint.html", template_vars)
    
    # Add Link preload header for opening hours if available
    if donationpoint.opening_hours and donationpoint.opening_hours.strip():
        openinghours_url = reverse("wfbn:foodbank_donationpoint_openinghours", kwargs={"slug": slug, "dpslug": dpslug})
        response["Link"] = f"<{openinghours_url}>; rel=preload; as=fetch"
    
    return response

@cache_page(SECONDS_IN_HOUR)
def foodbank_donationpoint_openinghours(request, slug, dpslug):
    """
    Food bank donation point opening hours
    """

    foodbank = get_object_or_404(Foodbank, slug = slug)
    donationpoint = get_object_or_404(FoodbankDonationPoint, slug = dpslug, foodbank = foodbank)
    if not donationpoint.opening_hours:
        return HttpResponseNotFound()

    template_vars = {
        "donationpoint":donationpoint,
    }

    response = render(request, "wfbn/foodbank/donationpoint_openinghours.html", template_vars)
    response["X-Robots-Tag"] = "noindex"
    return response


@cache_page(SECONDS_IN_WEEK)
def foodbank_donationpoint_photo(request, slug, dpslug):
    """
    Food bank donation point photo JPEG
    """

    size = request.GET.get("size", 1080)
    foodbank = get_object_or_404(Foodbank, slug = slug)
    donationpoint = get_object_or_404(FoodbankDonationPoint, slug = dpslug, foodbank = foodbank)

    if not donationpoint.place_has_photo:
        return HttpResponseNotFound()
    
    photo = photo_from_place_id(donationpoint.place_id, size)
    
    return HttpResponse(photo, content_type='image/jpeg')


@cache_page(SECONDS_IN_WEEK)
def constituencies(request):
    """
    Food bank constituencies index
    """

    postcode = request.GET.get("postcode", None)
    if postcode:
        admin_regions = admin_regions_from_postcode(postcode)
        parl_con = admin_regions.get("parliamentary_constituency", None)
        if parl_con:
            return HttpResponseRedirect(reverse("wfbn:constituency", kwargs={"slug":slugify(parl_con)}))

    constituencies = get_all_constituencies()

    template_vars = {
        "constituencies":constituencies,
        "postcode":postcode,
    }

    return render(request, "wfbn/constituency/index.html", template_vars)


@cache_page(SECONDS_IN_WEEK)
def constituency(request, slug):
    """
    Food bank constituency
    """

    constituency = get_object_or_404(ParliamentaryConstituency, slug = slug)

    map_config = {
        "geojson":reverse("wfbn:constituency_geojson", kwargs={"parlcon_slug":constituency.slug}),
        "max_zoom":14,
    }
    map_config = json.dumps(map_config)

    template_vars = {
        "constituency":constituency,
        "map_config":map_config,
    }

    return render(request, "wfbn/constituency/constituency.html", template_vars)


@csrf_exempt
def updates(request, slug, action):
    """
    Food bank updates pages
    Subscribe, confirm, unsubscribe acions
    """

    key = request.GET.get("key", None)
    email = request.POST.get("email", None)
    foodbank = get_object_or_404(Foodbank, slug=slug)

    if action == "subscribe":

        try:
            validate_email(email)
        except forms.ValidationError:
            return HttpResponseForbidden()
        
        turnstile_is_valid = validate_turnstile(request.POST.get("cf-turnstile-response"))

        if not turnstile_is_valid:
            return HttpResponseRedirect("%s?turnstilefail=true&email=%s" % (reverse("wfbn:foodbank_subscribe", kwargs={"slug":foodbank.slug}), email))

        # TODO - check subscriber dupe here, rather than inside the try

        try:
            new_sub = FoodbankSubscriber(
                foodbank = foodbank,
                email = email,
            )
            new_sub.save()

            template_vars = {
                "foodbank":foodbank,
                "sub_key":new_sub.sub_key,
            }

            text_body = render_to_string("wfbn/emails/confirm.txt", template_vars)
            html_body = render_to_string("wfbn/emails/confirm.html", template_vars)


            send_email(
                to = email,
                subject = "Confirm your Give Food subscription",
                body = text_body,
                html_body = html_body,
            )

            message = "Thanks, but we're not quite done yet.\n\nWe've sent an email to %s with a link to click to confirm your subscription. You might have to look in your spam folder though." % (email)

        except IntegrityError:

            message = "Sorry! That email address is already subscribed to that food bank."


    if action == "confirm":

        sub = get_object_or_404(FoodbankSubscriber, sub_key=key)

        if not sub.confirmed:
            sub.confirmed = True
            sub.save()

            template_vars = {
                "foodbank":sub.foodbank,
            }

            text_body = render_to_string("wfbn/emails/confirmed.txt", template_vars)
            html_body = render_to_string("wfbn/emails/confirmed.html", template_vars)

            send_email(
                to = sub.email,
                subject = "Thank you for confirming your subscription to %s Food Bank" % (foodbank.name),
                body = text_body,
                html_body = html_body,
            )

        message = "Great! Thank you for confirming your subscription."

    if action == "unsubscribe":

        if not key:
            return HttpResponseForbidden()

        sub = get_object_or_404(FoodbankSubscriber, unsub_key=key)
        sub.delete()

        message = "You have been unsubscribed."


    template_vars = {
        "section":"subscribe",
        "foodbank":foodbank,
        "message":message,
    }
    return render(request, "wfbn/foodbank/updates.html", template_vars)


@never_cache
def foodbank_hit(request, slug):
    """
    Food bank hit counter
    """
    foodbank = get_object_or_404(Foodbank, slug=slug)
    day = datetime.date.today()

    try:
        hit, created = FoodbankHit.objects.get_or_create(
            foodbank=foodbank,
            day=day,
            defaults={"hits": 1}
        )
    except FoodbankHit.MultipleObjectsReturned:
        hits = FoodbankHit.objects.filter(foodbank=foodbank, day=day)
        total_hits = sum(h.hits for h in hits)
        hits.delete()
        hit = FoodbankHit.objects.create(foodbank=foodbank, day=day, hits=total_hits + 1)
        created = True
    if not created:
        FoodbankHit.objects.filter(pk=hit.pk).update(hits=hit.hits + 1)

    return render(request, "wfbn/foodbank/hit.js", content_type="text/javascript")
