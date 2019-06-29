from django.db import models
from django.template.defaultfilters import slugify

from const.general import DELIVERY_HOURS


class Foodbank(models.Model):

    name = models.CharField(max_length=50)
    slug = models.CharField(max_length=50)
    address = models.TextField()
    latt_long = models.CharField(max_length=50)

    contact_email = models.EmailField()
    notification_email = models.EmailField()
    phone_number = models.CharField(max_length=20)

    shopping_list_url = models.URLField(max_length=200)

    created = models.DateTimeField(auto_now_add=True, editable=False)
    modified = models.DateTimeField(auto_now=True, editable=False)

    last_order = models.DateField(editable=False)


class Order(models.Model):

    foodbank = models.ForeignKey(Foodbank)
    items_text = models.TextField()
    id = models.CharField(max_length=20, editable=False)

    created = models.DateTimeField(auto_now_add=True, editable=False)
    modified = models.DateTimeField(auto_now=True, editable=False)

    delivery_date = models.DateField()
    delivery_hour = models.IntegerField(choices=DELIVERY_HOURS)

    weight = models.PositiveIntegerField(editable=False)
    calories = models.PositiveIntegerField(editable=False)
    cost = models.PositiveIntegerField(editable=False) #pence
    no_lines = models.PositiveIntegerField(editable=False)
    no_items = models.PositiveIntegerField(editable=False)

    def save(self, *args, **kwargs):
        # create ID from fbname and order date
        pass

    def lines(self):
        return OrderLine.objects.filter(order = self)


class OrderLine(models.Model):

    foodbank = models.ForeignKey(Foodbank)
    order = models.ForeignKey(Order)

    name = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField()
    cost = models.PositiveIntegerField() #pence

    weight = models.PositiveIntegerField(editable=False)
    calories = models.PositiveIntegerField(editable=False)
