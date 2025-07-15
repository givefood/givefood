import datetime
from itertools import chain

from django.shortcuts import get_object_or_404, render
from django.http import HttpResponseBadRequest
from django.views.decorators.cache import cache_page

from django_earthdistance.models import EarthDistance, LlToEarth

from givefood.models import Foodbank, FoodbankChange, FoodbankDonationPoint, ParliamentaryConstituency, FoodbankChange
from .func import ApiResponse
from givefood.func import find_locations, get_all_open_foodbanks, get_all_open_locations, geocode, is_uk, miles
from givefood.const.cache_times import SECONDS_IN_HOUR, SECONDS_IN_DAY, SECONDS_IN_MONTH, SECONDS_IN_WEEK

DEFAULT_FORMAT = "json"


@cache_page(SECONDS_IN_DAY)
def index(request):
    return render(request, "index.html")


@cache_page(SECONDS_IN_DAY)
def docs(request):

    api_formats = ["JSON","XML","YAML"]

    eg_foodbanks = [
        "Sid Valley",
        "Kingsbridge",
        "Meon Valley",
        "Black Country",
    ]

    eg_searches = [
        {"type":"address","query":"12 Millbank, Westminster, London SW1P 4QE"},
        {"type":"address","query":"Mount Pleasant Rd, Porthleven, Helston TR13 9JSE"},
        {"type":"address","query":"Gartocharn, Scotland"},
        {"type":"address","query":"Bexhill-on-Sea"},
        {"type":"address","query":"ZE2 9AU"},
        {"type":"lat_lng","query":"51.178889,-1.826111"},
        {"type":"lat_lng","query":"52.090833,0.131944"},
    ]

    eg_needs_obj = FoodbankChange.objects.filter(published=True).order_by("-created")[:5]
    eg_needs = []
    for eg_need in eg_needs_obj:
        eg_needs.append(eg_need.need_id)

    eg_parl_cons_obj = ParliamentaryConstituency.objects.all().order_by("?")[:5]
    eg_parl_cons = []
    for eg_parl_con in eg_parl_cons_obj:
        eg_parl_cons.append(eg_parl_con.name)

    template_vars = {
        "api_formats":api_formats,
        "eg_foodbanks":eg_foodbanks,
        "eg_searches":eg_searches,
        "eg_needs":eg_needs,
        "eg_parl_cons":eg_parl_cons,
    }

    return render(request, "docs.html", template_vars)


@cache_page(SECONDS_IN_WEEK)
def foodbanks(request):

    format = request.GET.get("format", DEFAULT_FORMAT)

    foodbanks = get_all_open_foodbanks()
    response_list = []

    if format != "geojson":
        for foodbank in foodbanks:
            response_list.append({
                "id": str(foodbank.uuid),
                "name":foodbank.full_name(),
                "alt_name":foodbank.alt_name,
                "slug":foodbank.slug,
                "phone":foodbank.phone_number,
                "secondary_phone":foodbank.secondary_phone_number,
                "email":foodbank.contact_email,
                "address":foodbank.full_address(),
                "postcode":foodbank.postcode,
                "closed":foodbank.is_closed,
                "country":foodbank.country,
                "lat_lng":foodbank.latt_long,
                "network":foodbank.network,
                "created":datetime.datetime.fromtimestamp(foodbank.created.timestamp()),
                "urls": {
                    "self":"https://www.givefood.org.uk/api/2/foodbank/%s/" % (foodbank.slug),
                    "html":"https://www.givefood.org.uk/needs/at/%s/" % (foodbank.slug),
                    "homepage":foodbank.url,
                    "shopping_list":foodbank.shopping_list_url,
                },
                "charity": {
                    "registration_id":foodbank.charity_number,
                    "register_url":foodbank.charity_register_url(),
                },
                "politics": {
                    "parliamentary_constituency":foodbank.parliamentary_constituency_name,
                    "mp":foodbank.mp,
                    "mp_party":foodbank.mp_party,
                    "mp_parl_id":foodbank.mp_parl_id,
                    "ward":foodbank.ward,
                    "district":foodbank.district,
                    "urls": {
                        "self":"https://www.givefood.org.uk/api/2/constituency/%s/" % (foodbank.parliamentary_constituency_slug),
                        "html":"https://www.givefood.org.uk/needs/in/constituency/%s/" % (foodbank.parliamentary_constituency_slug),
                    },
                }
            })
    else:
        features = []
        for foodbank in foodbanks:
            features.append(
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [float(foodbank.latt_long.split(",")[1]), float(foodbank.latt_long.split(",")[0])]
                    },
                    "properties": {
                        "name": foodbank.name,
                        "slug": foodbank.slug,
                        "address": foodbank.full_address(),
                        "country": foodbank.country,
                        "url": "https://www.givefood.org.uk/needs/at/%s/" % (foodbank.slug),
                        "json": "https://www.givefood.org.uk/api/2/foodbank/%s/" % (foodbank.slug),
                        "network": foodbank.network,
                        "email": foodbank.contact_email,
                        "telephone": foodbank.phone_number,
                        "parliamentary_constituency": foodbank.parliamentary_constituency_name,
                    }
                }
            )

        response_list = {
            "type": "FeatureCollection",
            "features": features
        }

    return ApiResponse(response_list, "foodbanks", format)


@cache_page(SECONDS_IN_MONTH)
def foodbank(request, slug):

    format = request.GET.get("format", DEFAULT_FORMAT)
    foodbank = get_object_or_404(Foodbank.objects.select_related("latest_need"), slug = slug)
    locations = foodbank.locations()

    if format != "geojson":
        location_list = []
        for location in locations:
            location_list.append(
                {
                    "name":location.name,
                    "slug":location.slug,
                    "address":location.full_address(),
                    "postcode":location.postcode,
                    "lat_lng":location.latt_long,
                    "phone":location.phone_number,
                    "politics": {
                        "parliamentary_constituency":location.parliamentary_constituency_name,
                        "mp":location.mp,
                        "mp_party":location.mp_party,
                        "mp_parl_id":foodbank.mp_parl_id,
                        "ward":location.ward,
                        "district":location.district,
                        "urls": {
                            "self":"https://www.givefood.org.uk/api/2/constituency/%s/" % (location.parliamentary_constituency_slug),
                            "html":"https://www.givefood.org.uk/needs/in/constituency/%s/" % (location.parliamentary_constituency_slug),
                        },
                    }
                }
            )

        nearby_foodbank_list = []
        for nearby_foodbank in foodbank.nearby():
            nearby_foodbank_list.append(
                {
                    "name":nearby_foodbank.name,
                    "slug":nearby_foodbank.slug,
                    "urls": {
                        "self":"https://www.givefood.org.uk/api/2/foodbank/%s/" % (nearby_foodbank.slug),
                        "html":"https://www.givefood.org.uk/needs/at/%s/" % (nearby_foodbank.slug),
                        "homepage":nearby_foodbank.url,
                        "shopping_list":nearby_foodbank.shopping_list_url,
                    },
                    "address":nearby_foodbank.full_address(),
                    "lat_lng":nearby_foodbank.latt_long,
                }
            )

        response_dict = {
            "id": str(foodbank.uuid),
            "name":foodbank.name,
            "alt_name":foodbank.alt_name,
            "slug":foodbank.slug,
            "phone":foodbank.phone_number,
            "secondary_phone":foodbank.secondary_phone_number,
            "email":foodbank.contact_email,
            "address":foodbank.full_address(),
            "postcode":foodbank.postcode,
            "closed":foodbank.is_closed,
            "lat_lng":foodbank.latt_long,
            "network":foodbank.network,
            "created":datetime.datetime.fromtimestamp(foodbank.created.timestamp()),
            "urls": {
                "self":"https://www.givefood.org.uk/api/2/foodbank/%s/" % (foodbank.slug),
                "html":"https://www.givefood.org.uk/needs/at/%s/" % (foodbank.slug),
                "homepage":foodbank.url,
                "shopping_list":foodbank.shopping_list_url,
                "map":"https://www.givefood.org.uk/needs/at/%s/map.png" % (foodbank.slug),
            },
            "charity": {
                "registration_id":foodbank.charity_number,
                "register_url":foodbank.charity_register_url(),
            },
            "locations": location_list,
            "politics": {
                "parliamentary_constituency":foodbank.parliamentary_constituency_name,
                "mp":foodbank.mp,
                "mp_party":foodbank.mp_party,
                "ward":foodbank.ward,
                "district":foodbank.district,
                "urls": {
                    "self":"https://www.givefood.org.uk/api/2/constituency/%s/" % (foodbank.parliamentary_constituency_slug),
                    "html":"https://www.givefood.org.uk/needs/in/constituency/%s/" % (foodbank.parliamentary_constituency_slug),
                },
            },
            "need": {
                "id":foodbank.latest_need.need_id,
                "needs":foodbank.latest_need.change_text,
                "excess":foodbank.latest_need.excess_change_text,
                "created":datetime.datetime.fromtimestamp(foodbank.latest_need.created.timestamp()),
                "self":"https://www.givefood.org.uk/api/2/need/%s/" % (foodbank.latest_need.need_id),
            },
            "nearby_foodbanks": nearby_foodbank_list,
        }
    else:
        features = []
        features.append(
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [float(foodbank.latt_long.split(",")[1]), float(foodbank.latt_long.split(",")[0])]
                    },
                    "properties": {
                        "name": foodbank.name,
                        "slug": foodbank.slug,
                        "address": foodbank.full_address(),
                        "url": "https://www.givefood.org.uk/needs/at/%s/" % (foodbank.slug),
                        "network": foodbank.network,
                        "email": foodbank.contact_email,
                        "telephone": foodbank.phone_number,
                        "parliamentary_constituency": foodbank.parliamentary_constituency_name,
                    }
                }
            )
        for location in locations:
            features.append(
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [float(location.latt_long.split(",")[1]), float(location.latt_long.split(",")[0])]
                    },
                    "properties": {
                        "name": location.name,
                        "slug": location.slug,
                        "address": location.full_address(),
                        "url": "https://www.givefood.org.uk/needs/at/%s/%s/" % (location.foodbank_slug, location.slug),
                        "network": location.foodbank_network,
                        "email": location.email_or_foodbank_email(),
                        "telephone": location.phone_or_foodbank_phone(),
                        "parliamentary_constituency": location.parliamentary_constituency_name,
                    }
                }
            )

        response_dict = {
            "type": "FeatureCollection",
            "features": features
        }

    return ApiResponse(response_dict, "foodbank", format)


@cache_page(SECONDS_IN_DAY)
def foodbank_search(request):

    format = request.GET.get("format", DEFAULT_FORMAT)
    lat_lng = request.GET.get("lat_lng")
    address = request.GET.get("address")

    # Check we either have lat_lng or address
    if not lat_lng and not address:
        return HttpResponseBadRequest()

    if lat_lng:
        # Check comma in lat_lng
        if "," not in lat_lng:
            return HttpResponseBadRequest()
        # Check lat_lng is contains only numbers
        if not lat_lng.replace(",","").replace("-","").replace(".","").isdigit():
            return HttpResponseBadRequest()

    # Attempt geocoding if we have an address    
    if address and not lat_lng:
        lat_lng = geocode(address)

    # Check lat_lng is in the UK
    if not is_uk(lat_lng):
        return HttpResponseBadRequest()
    
    lat = lat_lng.split(",")[0]
    lng = lat_lng.split(",")[1]

    foodbanks = Foodbank.objects.select_related("latest_need").filter(is_closed = False).annotate(
        distance=EarthDistance([
            LlToEarth([lat, lng]),
            LlToEarth(['latitude', 'longitude'])
        ])).order_by("distance")[:10]
    
    response_list = []

    for foodbank in foodbanks:
        latest_need = foodbank.latest_need
        response_list.append({
            "id": str(foodbank.uuid),
            "name":foodbank.name,
            "alt_name":foodbank.alt_name,
            "slug":foodbank.slug,
            "phone":foodbank.phone_number,
            "secondary_phone":foodbank.secondary_phone_number,
            "email":foodbank.contact_email,
            "address":foodbank.full_address(),
            "postcode":foodbank.postcode,
            "lat_lng":foodbank.latt_long,
            "distance_m":int(foodbank.distance),
            "distance_mi":round(miles(foodbank.distance),2),
            "needs": {
                "id":latest_need.need_id,
                "needs":latest_need.change_text,
                "excess":latest_need.excess_change_text,
                "found":datetime.datetime.fromtimestamp(latest_need.created.timestamp()),
                "number":latest_need.no_items(),
            },
            "urls": {
                "self":"https://www.givefood.org.uk/api/2/foodbank/%s/" % (foodbank.slug),
                "html":"https://www.givefood.org.uk/needs/at/%s/" % (foodbank.slug),
                "homepage":foodbank.url,
                "shopping_list":foodbank.shopping_list_url,
                "map":"https://www.givefood.org.uk/needs/at/%s/map.png" % (foodbank.slug),
            },
            "charity": {
                "registration_id":foodbank.charity_number,
                "register_url":foodbank.charity_register_url(),
            },
            "politics": {
                "parliamentary_constituency":foodbank.parliamentary_constituency_name,
                "mp":foodbank.mp,
                "mp_party":foodbank.mp_party,
                "mp_parl_id":foodbank.mp_parl_id,
                "ward":foodbank.ward,
                "district":foodbank.district,
                "urls": {
                    "self":"https://www.givefood.org.uk/api/2/constituency/%s/" % (foodbank.parliamentary_constituency_slug),
                    "html":"https://www.givefood.org.uk/needs/in/constituency/%s/" % (foodbank.parliamentary_constituency_slug),
                },
            }
        })

    return ApiResponse(response_list, "foodbanks", format)


@cache_page(SECONDS_IN_MONTH)
def locations(request):

    format = request.GET.get("format", DEFAULT_FORMAT)

    locations = get_all_open_locations()
    response_list = []

    if format != "geojson":
        for location in locations:

            response_list.append({
                "id": str(location.uuid),
                "name":location.name,
                "slug":location.slug,
                "phone":location.phone_or_foodbank_phone(),
                "email":location.email_or_foodbank_email(),
                "address":location.full_address(),
                "postcode":location.postcode,
                "lat_lng":location.latt_long,
                "urls": {
                    "html":"https://www.givefood.org.uk/needs/at/%s/%s/" % (location.foodbank_slug, location.slug)
                },
                "foodbank": {
                    "name":location.foodbank_name,
                    "slug":location.foodbank_slug,
                    "network":location.foodbank_network,
                    "urls": {
                        "self":"https://www.givefood.org.uk/api/2/foodbank/%s/" % (location.foodbank_slug),
                        "html":"https://www.givefood.org.uk/needs/at/%s/" % (location.foodbank_slug)
                    },
                },
                "politics": {
                    "parliamentary_constituency":location.parliamentary_constituency_name,
                    "mp":location.mp,
                    "mp_party":location.mp_party,
                    "mp_parl_id":location.mp_parl_id,
                    "ward":location.ward,
                    "district":location.district,
                    "urls": {
                        "self":"https://www.givefood.org.uk/api/2/constituency/%s/" % (location.parliamentary_constituency_slug),
                        "html":"https://www.givefood.org.uk/needs/in/constituency/%s/" % (location.parliamentary_constituency_slug),
                    },
                }
            })
    else:

        features = []
        for location in locations:
            features.append(
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [float(location.latt_long.split(",")[1]), float(location.latt_long.split(",")[0])]
                    },
                    "properties": {
                        "name": location.full_name(),
                        "slug": location.slug,
                        "address": location.full_address(),
                        "url": "https://www.givefood.org.uk/needs/at/%s/%s/" % (location.foodbank_slug, location.slug),
                        "network": location.foodbank_network,
                        "email": location.email_or_foodbank_email(),
                        "telephone": location.phone_or_foodbank_phone(),
                        "foodbank": location.foodbank_name,
                        "foodbank_slug": location.foodbank_slug,
                        "foodbank_url": "https://www.givefood.org.uk/needs/at/%s/" % (location.foodbank_slug),
                        "parliamentary_constituency": location.parliamentary_constituency_name,
                    }
                }
            )

        response_list = {
            "type": "FeatureCollection",
            "features": features
        }

    return ApiResponse(response_list, "locations", format)


@cache_page(SECONDS_IN_DAY)
def location_search(request):

    format = request.GET.get("format", DEFAULT_FORMAT)
    lat_lng = request.GET.get("lat_lng")
    address = request.GET.get("address")

    if not lat_lng and not address:
        return HttpResponseBadRequest()

    if address and not lat_lng:
        lat_lng = geocode(address)

    if not is_uk(lat_lng):
        return HttpResponseBadRequest() 

    foodbanksandlocations = find_locations(lat_lng, 20, False)

    response_list = []

    for item in foodbanksandlocations:

        item_dict = {
            "id": str(item.uuid),
            "type":item.type,
            "slug":item.slug,
            "name":item.name,
            "lat_lng":item.latt_long,
            "distance_m":int(item.distance),
            "distance_mi":round(miles(item.distance),2),
            "address":item.full_address(),
            "postcode":item.postcode,
            "politics": {
                "parliamentary_constituency":item.parliamentary_constituency_name,
                "mp":item.mp,
                "mp_party":item.mp_party,
                "mp_parl_id":item.mp_parl_id,
                "ward":item.ward,
                "district":item.district,
                "urls": {
                    "self":"https://www.givefood.org.uk/api/2/constituency/%s/" % (item.parliamentary_constituency_slug),
                    "html":"https://www.givefood.org.uk/needs/in/constituency/%s/" % (item.parliamentary_constituency_slug),
                },
            },
            "phone":item.phone_number,
            "email":item.contact_email,
            "needs": {
                "id":item.latest_need.need_id,
                "needs":item.latest_need.change_text,
                "excess":item.latest_need.excess_change_text,
                "number":item.latest_need.no_items(),
                "found":datetime.datetime.fromtimestamp(item.latest_need.created.timestamp()),
            },
            "foodbank": {
                "name":item.foodbank_name,
                "slug":item.foodbank_slug,
                "network":item.foodbank_network,
                "urls": {
                    "self":"https://www.givefood.org.uk/api/2/foodbank/%s/" % (item.foodbank_slug),
                    "html":"https://www.givefood.org.uk/needs/at/%s/" % (item.foodbank_slug),
                }
            },
            "urls": {
                "html": item.html_url,
                "homepage":item.homepage,
            },
        }
        
        response_list.append(item_dict)

    return ApiResponse(response_list, "locations", format)


@cache_page(SECONDS_IN_WEEK)
def donationpoints(request):

    format = request.GET.get("format", "geojson")
    if format != "geojson":
        return HttpResponseBadRequest()

    donationpoints = FoodbankDonationPoint.objects.filter(is_closed = False)

    features = []
    for donationpoint in donationpoints:
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(donationpoint.long()), float(donationpoint.latt())]
                },
                "properties": {
                    "name": donationpoint.name,
                    "slug": donationpoint.slug,
                    "address": donationpoint.full_address(),
                    "url": "https://www.givefood.org.uk/needs/at/%s/donationpoint/%s/" % (donationpoint.foodbank_slug, donationpoint.slug),
                    "network": donationpoint.foodbank_network,
                    "telephone": donationpoint.phone_number,
                    "web": donationpoint.url_with_ref(),
                    "foodbank": donationpoint.foodbank_name,
                    "foodbank_slug": donationpoint.foodbank_slug,
                    "foodbank_url": "https://www.givefood.org.uk/needs/at/%s/" % (donationpoint.foodbank_slug),
                    "parliamentary_constituency": donationpoint.parliamentary_constituency_name,
                }
            }
        )

    deliveryaddresses = Foodbank.objects.filter(is_closed = False).exclude(delivery_address__exact='')
    for deliveryaddress in deliveryaddresses:
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(deliveryaddress.delivery_long()), float(deliveryaddress.delivery_latt())]
                },
                "properties": {
                    "name": deliveryaddress.name + " delivery address",
                    "slug": deliveryaddress.slug,
                    "address": deliveryaddress.full_address(),
                    "url": "https://www.givefood.org.uk/needs/at/%s/" % (deliveryaddress.slug),
                    "network": deliveryaddress.network,
                    "telephone": deliveryaddress.phone_number,
                    "web": deliveryaddress.url_with_ref(),
                    "foodbank": deliveryaddress.name,
                    "foodbank_slug": deliveryaddress.slug,
                    "foodbank_url": "https://www.givefood.org.uk/needs/at/%s/" % (deliveryaddress.slug),
                    "parliamentary_constituency": deliveryaddress.parliamentary_constituency_name,
                }
            }
        )

    response_list = {
        "type": "FeatureCollection",
        "features": features
    }

    return ApiResponse(response_list, "donationpoints", format)


@cache_page(SECONDS_IN_HOUR)
def needs(request):

    format = request.GET.get("format", DEFAULT_FORMAT)

    needs = FoodbankChange.objects.filter(published = True).order_by("-created")[:100]

    response_list = []

    for need in needs:
        response_list.append({
            "id":need.need_id,
            "found":datetime.datetime.fromtimestamp(need.created.timestamp()),
            "foodbank": {
                "name":need.foodbank_name,
                "slug":str(need.foodbank_name_slug()),
                "urls": {
                    "self":"https://www.givefood.org.uk/api/2/foodbank/%s/" % (need.foodbank_name_slug()),
                    "html":"https://www.givefood.org.uk/needs/at/%s/" % (need.foodbank_name_slug()),
                }

            },
            "needs":need.change_text,
            "excess":need.excess_change_text,
            "self":"https://www.givefood.org.uk/api/2/need/%s/" % (need.need_id),
        })

    return ApiResponse(response_list, "needs", format)


@cache_page(SECONDS_IN_DAY)
def need(request, id):

    format = request.GET.get("format", DEFAULT_FORMAT)
    need = get_object_or_404(FoodbankChange, need_id = id)

    response_dict = {
        "id":need.need_id,
        "found":datetime.datetime.fromtimestamp(need.created.timestamp()),
        "foodbank": {
            "name":need.foodbank_name,
            "slug":str(need.foodbank_name_slug()),
            "urls": {
                "self":"https://www.givefood.org.uk/api/2/foodbank/%s/" % (need.foodbank_name_slug()),
                "html":"https://www.givefood.org.uk/needs/at/%s/" % (need.foodbank_name_slug()),
            }
        },
        "needs":need.change_text,
        "excess":need.excess_change_text,
        "self":"https://www.givefood.org.uk/api/2/need/%s/" % (need.need_id),
    }

    return ApiResponse(response_dict, "need", format)


@cache_page(SECONDS_IN_DAY)
def constituencies(request):

    format = request.GET.get("format", DEFAULT_FORMAT)

    constituencies = ParliamentaryConstituency.objects.all()

    response_list = []

    for constituency in constituencies:
        response_list.append({
            "name":constituency.name,
            "slug":constituency.slug,
            "country":constituency.country,
            "urls": {
                "self":"https://www.givefood.org.uk/api/2/constituency/%s/" % (constituency.slug),
                "html":"https://www.givefood.org.uk/needs/in/constituency/%s/" % (constituency.slug),
            }
        })

    return ApiResponse(response_list, "constituencies", format) 


@cache_page(SECONDS_IN_WEEK)
def constituency(request, slug):

    format = request.GET.get("format", DEFAULT_FORMAT)
    constituency = get_object_or_404(ParliamentaryConstituency, slug = slug)
    foodbanks = constituency.foodbanks()

    if format != "geojson":
        foodbank_list = []
        for foodbank in foodbanks:
            foodbank_list.append(
                {
                    "name":foodbank.get("name"),
                    "slug":foodbank.get("slug"),
                    "lat_lng":foodbank.get("lat_lng"),
                    "needs":foodbank.get("needs").change_text,
                    "excess":foodbank.get("needs").excess_change_text,
                    "urls": {
                        "self":"https://www.givefood.org.uk/api/2/foodbank/%s/" % (foodbank.get("slug")),
                        "html":"https://www.givefood.org.uk/needs/at/%s/" % (foodbank.get("slug")),
                        "homepage":foodbank.get("url"),
                        "shopping_list":foodbank.get("shopping_list_url"),
                        "map":"https://www.givefood.org.uk/needs/at/%s/map.png" % (foodbank.get("slug")),
                    },
                }
            )

        response_dict = {
            "name":constituency.name,
            "slug":constituency.slug,
            "foodbanks":foodbank_list,
        }
    else:
        features = []
        for foodbank in foodbanks:
            features.append(
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [float(foodbank.get("lat_lng").split(",")[1]), float(foodbank.get("lat_lng").split(",")[0])]
                    },
                    "properties": {
                        "name": foodbank.get("name"),
                        "slug": foodbank.get("slug"),
                        "needs": foodbank.get("needs").change_text,
                        "excess":foodbank.get("needs").excess_change_text,
                        "url": "https://www.givefood.org.uk%s" % (foodbank.get("gf_url")),
                    }
                }
            )

        features.append(constituency.boundary_geojson_dict())

        response_dict = {
            "type": "FeatureCollection",
            "features": features,
        }

    return ApiResponse(response_dict, "constituency", format)
