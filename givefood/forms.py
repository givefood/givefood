from django.forms import Form, ModelForm, DateInput, ModelChoiceField, HiddenInput
from django import forms

from models import Foodbank, Order, FoodbankChange, FoodbankLocation, ParliamentaryConstituency
from const.general import COUNTRIES_CHOICES, FOODBANK_NETWORK_CHOICES


class FoodbankRegistrationForm(forms.Form):
    name = forms.CharField(max_length=100, help_text="E.g. 'Brixton', 'Sid Valley', or 'One Can Trust'")
    address = forms.CharField(widget=forms.Textarea, help_text="Please include your postcode")
    country = forms.ChoiceField(choices=COUNTRIES_CHOICES)
    network = forms.ChoiceField(choices=FOODBANK_NETWORK_CHOICES)
    email = forms.EmailField()
    phone_number = forms.CharField(help_text="A public phone number, as this will be published")
    charity_number = forms.CharField(help_text="Optional. E.g. 1188192 or SC041954", required=False)
    website = forms.URLField(help_text="E.g. http://www.sidvalleyfoodbank.org.uk")
    shopping_list_link = forms.URLField(help_text="Optional. E.g. http://www.sidvalleyfoodbank.org.uk/shopping-list/", required=False)
    facebook = forms.URLField(help_text="Optional. E.g. https://www.facebook.com/SidValleyFoodBank", required=False)
    twitter = forms.URLField(help_text="Optional. E.g. https://twitter.com/BrixtonFoodbank/", required=False)


class FoodbankForm(ModelForm):
    class Meta:
        model = Foodbank
        fields = "__all__"
        exclude = ("parliamentary_constituency", "county", "district", "ward", "mp", "mp_party", "mp_parl_id")


class FoodbankPoliticsForm(ModelForm):
    class Meta:
        model = Foodbank
        fields = ("parliamentary_constituency", "county", "district", "ward", "mp", "mp_party", "mp_parl_id")


class FoodbankLocationForm(ModelForm):
    class Meta:
        model = FoodbankLocation
        fields = "__all__"
        widgets = {'foodbank': HiddenInput()}
        exclude = ("parliamentary_constituency", "county", "district", "ward", "mp", "mp_party", "mp_parl_id")


class FoodbankLocationPoliticsForm(ModelForm):
    class Meta:
        model = Foodbank
        fields = ("parliamentary_constituency", "county", "district", "ward", "mp", "mp_party", "mp_parl_id")

class OrderForm(ModelForm):
    foodbank = ModelChoiceField(queryset=Foodbank.objects.filter(is_closed = False).order_by('name'))
    need = ModelChoiceField(queryset=FoodbankChange.objects.all().order_by('-created'), required=False)
    class Meta:
        model = Order
        fields = "__all__"
        widgets = {
            'delivery_date': DateInput(attrs={'type': 'date'})
        }

    def __init__(self, *args, **kwargs):
        super(OrderForm, self).__init__(*args, **kwargs)
        if kwargs.get("initial"):
            if kwargs['initial']['foodbank']:
                queryset = FoodbankChange.objects.filter(
                    foodbank=kwargs['initial']['foodbank']
                ).order_by('-created')
                self.fields['need'].queryset = queryset


class NeedForm(ModelForm):
    foodbank = ModelChoiceField(queryset=Foodbank.objects.filter().order_by('name'), required=False)
    class Meta:
        model = FoodbankChange
        fields = "__all__"


class ParliamentaryConstituencyForm(ModelForm):
    class Meta:
        model = ParliamentaryConstituency
        fields = "__all__"
