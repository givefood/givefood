from givefood.func import get_all_foodbanks

def all_foodbanks(request):

    return {
        'all_foodbanks':get_all_foodbanks(),
    }
