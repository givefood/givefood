import logging

from django.shortcuts import get_object_or_404, render
from django.template import RequestContext
from django.http import HttpResponseBadRequest
from django.template.defaultfilters import slugify
from django.views.decorators.cache import cache_page, cache_control

from givefood.models import Foodbank, ApiFoodbankSearch, FoodbankChange, ParliamentaryConstituency, FoodbankChange
from .func import ApiResponse
from givefood.func import get_all_foodbanks, get_all_locations, find_foodbanks, geocode, find_locations, is_uk

DEFAULT_FORMAT = "json"


@cache_page(60*10)
def index(request):

    template_vars = {}

    return render(request, "index.html", template_vars)


@cache_page(60*10)
def docs(request):

    api_formats = ["JSON","XML","YAML"]

    eg_foodbanks = [
        "Sid Valley",
        "Kingsbridge",
        "Norwood & Brixton",
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

    eg_parl_cons = {
        "Uxbridge and South Ruislip",
        "Vauxhall",
        "Exeter",
        "Orkney and Shetland",
        "North Somerset",
    }

    template_vars = {
        "api_formats":api_formats,
        "eg_foodbanks":eg_foodbanks,
        "eg_searches":eg_searches,
        "eg_needs":eg_needs,
        "eg_parl_cons":eg_parl_cons,
    }

    return render(request, "docs.html", template_vars)


@cache_control(public=True, max_age=3600)
def foodbanks(request):

    format = request.GET.get("format", DEFAULT_FORMAT)

    foodbanks = get_all_foodbanks()
    response_list = []

    if format != "geojson":
        for foodbank in foodbanks:
            response_list.append({
                "name":foodbank.name,
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
                "created":foodbank.created,
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


@cache_page(60*20)
def foodbank(request, slug):

    format = request.GET.get("format", DEFAULT_FORMAT)
    foodbank = get_object_or_404(Foodbank, slug = slug)

    # Locations
    locations = foodbank.locations()
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
        "created":foodbank.created,
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
            "id":foodbank.latest_need_id(),
            "needs":foodbank.latest_need().clean_change_text(),
            "created":foodbank.latest_need_date(),
            "self":"https://www.givefood.org.uk/api/2/need/%s/" % (foodbank.latest_need_id()),
        },
        "nearby_foodbanks": nearby_foodbank_list,
    }

    return ApiResponse(response_dict, "foodbank", format)


@cache_page(60*20)
def foodbank_search(request):

    format = request.GET.get("format", DEFAULT_FORMAT)
    lat_lng = request.GET.get("lat_lng")
    address = request.GET.get("address")

    if not lat_lng and not address:
        return HttpResponseBadRequest()

    if address and not lat_lng:
        lat_lng = geocode(address)

    if not is_uk(lat_lng):
        return HttpResponseBadRequest() 

    foodbanks = find_foodbanks(lat_lng, 10)
    response_list = []

    if address:
        query_type = "address"
        query = address
    else:
        query_type = "lattlong"
        query = lat_lng

    api_hit = ApiFoodbankSearch(
        query_type = query_type,
        query = query,
        nearest_foodbank = foodbanks[0].distance_m,
        latt_long = lat_lng,
    )
    api_hit.save()

    response_list = []

    for foodbank in foodbanks:
        response_list.append({
            "name":foodbank.name,
            "alt_name":foodbank.alt_name,
            "slug":foodbank.slug,
            "phone":foodbank.phone_number,
            "secondary_phone":foodbank.secondary_phone_number,
            "email":foodbank.contact_email,
            "address":foodbank.full_address(),
            "postcode":foodbank.postcode,
            "lat_lng":foodbank.latt_long,
            "distance_m":int(foodbank.distance_m),
            "distance_mi":round(foodbank.distance_mi,2),
            "needs": {
                "needs":foodbank.latest_need().clean_change_text(),
                "found":foodbank.latest_need().created,
                "number":foodbank.latest_need().no_items(),
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


@cache_control(public=True, max_age=3600)
def locations(request):

    format = request.GET.get("format", DEFAULT_FORMAT)

    locations = get_all_locations()
    response_list = []

    if format != "geojson":
        for location in locations:

            response_list.append({
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

        response_list = {
            "type": "FeatureCollection",
            "features": features
        }

    return ApiResponse(response_list, "locations", format)


@cache_page(60*20)
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

    locations = find_locations(lat_lng, 10)

    if address:
        query_type = "address"
        query = address
    else:
        query_type = "lattlong"
        query = lat_lng

    api_hit = ApiFoodbankSearch(
        query_type = query_type,
        query = query,
        nearest_foodbank = locations[0].get("distance_m"),
        latt_long = lat_lng,
    )
    api_hit.save()

    response_list = []
    for location in locations:

        location_need = FoodbankChange.objects.filter(foodbank_name=location.get("foodbank_name"), published=True).latest("created")

        if location.get("type") == "location":
            html_url = "https://www.givefood.org.uk/needs/at/%s/%s/" % (slugify(location.get("foodbank_name")), slugify(location.get("name")))
        if location.get("type") == "organisation":
            html_url = "https://www.givefood.org.uk/needs/at/%s/" % (slugify(location.get("foodbank_name")))

        response_list.append({
            "type":location.get("type"),
            "name":location.get("name"),
            "lat_lng":location.get("lat_lng"),
            "distance_m":int(location.get("distance_m")),
            "distance_mi":round(location.get("distance_mi"),2),
            "phone":location.get("phone"),
            "email":location.get("email"),
            "foodbank": {
                "name":location.get("foodbank_name"),
                "slug":str(slugify(location.get("foodbank_name"))),
                "network":location.get("foodbank_network"),
                "urls": {
                    "self":"https://www.givefood.org.uk/api/2/foodbank/%s/" % slugify(location.get("foodbank_name")),
                    "html":"https://www.givefood.org.uk/needs/at/%s/" % slugify(location.get("foodbank_name")),
                }
            },
            "needs": {
                "needs":location_need.clean_change_text(),
                "number":location_need.no_items(),
                "found":location_need.created,
            },
            "address":location.get("address"),
            "postcode":location.get("postcode"),
            "politics": {
                "parliamentary_constituency":location.get("parliamentary_constituency"),
                "mp":location.get("mp"),
                "mp_party":location.get("mp_party"),
                "mp_parl_id":location.get("mp_parl_id"),
                "ward":location.get("ward"),
                "district":location.get("district"),
                "urls": {
                    "self":"https://www.givefood.org.uk/api/2/constituency/%s/" % (location.get("parliamentary_constituency_slug")),
                    "html":"https://www.givefood.org.uk/needs/in/constituency/%s/" % (location.get("parliamentary_constituency_slug")),
                },
            },
            "urls": {
                "html":html_url,
            },
        })

    return ApiResponse(response_list, "locations", format)


@cache_page(60*5)
def needs(request):

    format = request.GET.get("format", DEFAULT_FORMAT)

    needs = FoodbankChange.objects.filter(published = True).order_by("-created")[:100]

    response_list = []

    for need in needs:
        response_list.append({
            "id":need.need_id,
            "found":need.created,
            "foodbank": {
                "name":need.foodbank_name,
                "slug":str(need.foodbank_name_slug()),
                "urls": {
                    "self":"https://www.givefood.org.uk/api/2/foodbank/%s/" % (need.foodbank_name_slug()),
                    "html":"https://www.givefood.org.uk/needs/at/%s/" % (need.foodbank_name_slug()),
                }

            },
            "needs":need.clean_change_text(),
            "self":"https://www.givefood.org.uk/api/2/needs/%s/" % (need.need_id),
        })

    return ApiResponse(response_list, "needs", format)


@cache_page(60*10)
def need(request, id):

    format = request.GET.get("format", DEFAULT_FORMAT)
    need = get_object_or_404(FoodbankChange, need_id = id)

    response_dict = {
        "id":need.need_id,
        "found":need.created,
        "foodbank": {
            "name":need.foodbank_name,
            "slug":str(need.foodbank_name_slug()),
            "urls": {
                "self":"https://www.givefood.org.uk/api/2/foodbank/%s/" % (need.foodbank_name_slug()),
                "html":"https://www.givefood.org.uk/needs/at/%s/" % (need.foodbank_name_slug()),
            }
        },
        "needs":need.clean_change_text(),
        "self":"https://www.givefood.org.uk/api/2/needs/%s/" % (need.need_id),
    }

    return ApiResponse(response_dict, "need", format)


@cache_page(60*20)
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
                    "needs":foodbank.get("needs").clean_change_text(),
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
            "mp": {
                "name":constituency.mp,
                "party":constituency.mp_party,
                "id":constituency.mp_parl_id,
                "urls": {
                    "html":"https://members.parliament.uk/member/%s/contact" % (constituency.mp_parl_id),
                    "photo":"https://www.givefood.org.uk/needs/in/constituency/%s/mp_photo_threefour.png" % (constituency.slug),
                }
            },
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
