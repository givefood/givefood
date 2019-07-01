from django.forms import ModelForm

from models import Foodbank, Order


class FoodbankForm(ModelForm):
    class Meta:
        model = Foodbank
        fields = "__all__"


class OrderForm(ModelForm):
    class Meta:
        model = Order
        fields = "__all__"
