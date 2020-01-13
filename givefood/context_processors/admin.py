from givefood.models import Foodbank

def all_foodbanks(request):

    foodbanks = Foodbank.objects.all()

    return {
        'all_foodbanks':foodbanks,
    }
