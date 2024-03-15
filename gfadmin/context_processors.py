from givefood.func import get_cred

def gmap_keys(request):

    return {
        'gmap_key':get_cred("gmap_key"),
        'gmap_static_key':get_cred("gmap_static_key"),
        'gmap_geocode_key':get_cred("gmap_geocode_key"),
        'gmap_places_key':get_cred("gmap_places_key"),
    }
