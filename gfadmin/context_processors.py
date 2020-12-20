from givefood.func import get_all_foodbanks, get_cred

def all_foodbanks(request):

    return {
        'all_foodbanks':get_all_foodbanks(),
    }

def gmap_keys(request):

    return {
        'gmap_key':get_cred("gmap_key"),
        'gmap_static_key':get_cred("gmap_static_key"),
        'gmap_geocode_key':get_cred("gmap_geocode_key")
    }
