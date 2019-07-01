from django.db import models
from django.template.defaultfilters import slugify

from const.general import DELIVERY_HOURS_CHOICES


class Foodbank(models.Model):

    name = models.CharField(max_length=50)
    slug = models.CharField(max_length=50, editable=False)
    address = models.TextField()
    latt_long = models.CharField(max_length=50, verbose_name="Latt,Long")

    contact_email = models.EmailField()
    notification_email = models.EmailField()
    phone_number = models.CharField(max_length=20)

    url = models.URLField(max_length=200, verbose_name="URL")
    shopping_list_url = models.URLField(max_length=200, verbose_name="Shopping list URL")

    created = models.DateTimeField(auto_now_add=True, editable=False)
    modified = models.DateTimeField(auto_now=True, editable=False)

    last_order = models.DateField(editable=False,null=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super(Foodbank, self).save(*args, **kwargs)


class Order(models.Model):

    foodbank = models.ForeignKey(Foodbank)
    items_text = models.TextField()
    id = models.CharField(max_length=20, editable=False, primary_key=True)

    created = models.DateTimeField(auto_now_add=True, editable=False)
    modified = models.DateTimeField(auto_now=True, editable=False)

    delivery_date = models.DateField()
    delivery_hour = models.IntegerField(choices=DELIVERY_HOURS_CHOICES)
    delivery_datetime = models.DateTimeField(editable=False)

    weight = models.PositiveIntegerField(editable=False)
    calories = models.PositiveIntegerField(editable=False)
    cost = models.PositiveIntegerField(editable=False) #pence
    no_lines = models.PositiveIntegerField(editable=False)
    no_items = models.PositiveIntegerField(editable=False)

    def delivery_datetime(self):
        # calculate from delivery_date & delivery_hour
        pass

    def save(self, *args, **kwargs):
        # create ID from fbname and order date
        # record delivery_datetime
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
