from django.shortcuts import get_object_or_404

from givefood.models import Foodbank
from .func import ApiResponse
from givefood.func import get_all_foodbanks

DEFAULT_FORMAT = "json"


def foodbanks(request):

    format = request.GET.get("format", DEFAULT_FORMAT)

    foodbanks = get_all_foodbanks()
    response_list = []

    for foodbank in foodbanks:
        response_list.append({
            "name":foodbank.name,
            "alt_name":foodbank.alt_name,
            "slug":foodbank.slug,
            "phone":foodbank.phone_number,
            "email":foodbank.contact_email,
            "address":foodbank.full_address(),
            "postcode":foodbank.postcode,
            "closed":foodbank.is_closed,
            "lat_lng":foodbank.latt_long,
            "network":foodbank.network,
            "modified":foodbank.modified,
            "urls": {
                "self":"https://www.givefood.org.uk/api/2/foodbank/%s/" % (foodbank.slug),
                "html":"https://www.givefood.org.uk/needs/at/%s/" % (foodbank.slug),
            },
            "charity": {
                "registration_id":foodbank.charity_number,
                "register_url":foodbank.charity_register_url(),
            },
            "politics": {
                "parliamentary_constituency":foodbank.parliamentary_constituency,
                "mp":foodbank.mp,
                "mp_party":foodbank.mp_party,
                "ward":foodbank.ward,
                "district":foodbank.district,
                "urls": {
                    "self":"https://www.givefood.org.uk/api/2/constituency/%s/" % (foodbank.parliamentary_constituency_slug),
                    "html":"https://www.givefood.org.uk/needs/in/constituency/%s/" % (foodbank.parliamentary_constituency_slug),
                },
            }
        })

    return ApiResponse(response_list, "foodbanks", format)


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
                "address":location.full_address(),
                "postcode":location.postcode,
                "lat_lng":location.latt_long,
                "phone":location.phone_number,
                "politics": {
                    "parliamentary_constituency":location.parliamentary_constituency,
                    "mp":location.mp,
                    "mp_party":location.mp_party,
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
        "email":foodbank.contact_email,
        "address":foodbank.full_address(),
        "postcode":foodbank.postcode,
        "closed":foodbank.is_closed,
        "lat_lng":foodbank.latt_long,
        "network":foodbank.network,
        "modified":foodbank.modified,
        "urls": {
            "self":"https://www.givefood.org.uk/api/2/foodbank/%s/" % (foodbank.slug),
            "html":"https://www.givefood.org.uk/needs/at/%s/" % (foodbank.slug),
        },
        "charity": {
            "registration_id":foodbank.charity_number,
            "register_url":foodbank.charity_register_url(),
        },
        "locations": location_list,
        "politics": {
            "parliamentary_constituency":foodbank.parliamentary_constituency,
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
            "needs":str(foodbank.latest_need_text()),
            "created":foodbank.latest_need_date(),
            "self":"https://www.givefood.org.uk/api/2/need/%s/" % (foodbank.latest_need_id()),
        },
        "nearby_foodbanks": nearby_foodbank_list,
    }

    return ApiResponse(response_dict, "foodbank", format)