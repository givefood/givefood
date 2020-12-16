from givefood.func import get_all_foodbanks, get_cred

def all_foodbanks(request):

    return {
        'all_foodbanks':get_all_foodbanks(),
    }

def gmap_key(request):

    return {
        'gmap_key':get_cred("gmap_key"),
    }
