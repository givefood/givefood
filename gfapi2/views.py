from django.shortcuts import get_object_or_404

from givefood.models import Foodbank
from .func import ApiResponse

DEFAULT_FORMAT = "json"


def foodbanks(request):
    pass


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
            "needs":foodbank.latest_need_text(),
            "created":foodbank.latest_need_date(),
        }
    }

    return ApiResponse(response_dict, "foodbank", format)