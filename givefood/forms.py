from datetime import datetime

from django.forms import ModelForm, DateInput, ModelChoiceField, HiddenInput
from django import forms
from givefood.models import FoodbankDonationPoint, OrderGroup, Foodbank, Order, FoodbankChange, FoodbankLocation, ParliamentaryConstituency, OrderItem, GfCredential, FoodbankGroup, FoodbankChangeLine, SlugRedirect
from givefood.const.general import COUNTRIES_CHOICES, FOODBANK_NETWORK_CHOICES


class FoodbankRegistrationForm(forms.Form):
    name = forms.CharField(max_length=100, help_text="E.g. 'Brixton', 'Sid Valley', or 'One Can Trust'")
    address = forms.CharField(widget=forms.Textarea)
    postcode = forms.CharField(max_length=10)
    country = forms.ChoiceField(choices=COUNTRIES_CHOICES)
    network = forms.ChoiceField(choices=FOODBANK_NETWORK_CHOICES)
    email = forms.EmailField(help_text="A public email address, as this will be published")
    phone_number = forms.CharField(help_text="A public phone number, as this will be published")
    charity_number = forms.CharField(help_text="Optional. E.g. 1188192 or SC041954", required=False)
    website = forms.URLField(help_text="E.g. http://www.sidvalleyfoodbank.org.uk")
    shopping_list_link = forms.URLField(help_text="Optional. E.g. http://www.sidvalleyfoodbank.org.uk/shopping-list/", required=False)
    facebook = forms.URLField(help_text="Optional. E.g. https://www.facebook.com/SidValleyFoodBank", required=False)
    twitter = forms.URLField(help_text="Optional. E.g. https://twitter.com/BrixtonFoodbank/", required=False)


class FlagForm(forms.Form):
    our_page = forms.URLField(help_text="Address of the page you're flagging")
    your_email = forms.EmailField(help_text="Optional. Your email address", required=False)
    explanation = forms.CharField(widget=forms.Textarea, help_text="Optional. Please explain why you're flagging this page", required=False)


class FoodbankForm(ModelForm):
    class Meta:
        model = Foodbank
        fields = "__all__"

    def save(self, commit=True): 
        foodbank = super().save(commit=False)
        foodbank.edited = datetime.now()
        
        if commit:
            foodbank.save()
        return foodbank


class FoodbankUrlsForm(ModelForm):
    class Meta:
        model = Foodbank
        fields = ["url", "shopping_list_url", "rss_url", "donation_points_url", "locations_url", "contacts_url"]

    def save(self, commit=True): 
        foodbank = super().save(commit=False)
        foodbank.edited = datetime.now()
        
        if commit:
            foodbank.save()
        return foodbank


class FoodbankPoliticsForm(ModelForm):
    class Meta:
        model = Foodbank
        fields = "__all__"


class FoodbankGroupForm(ModelForm):
    class Meta:
        model = FoodbankGroup
        fields = "__all__"


class FoodbankLocationForm(ModelForm):
    class Meta:
        model = FoodbankLocation
        fields = "__all__"
        widgets = {'foodbank': HiddenInput()}
        exclude = ('is_closed',)

    def save(self, commit=True): 
        location = super().save(commit=False)
        location.edited = datetime.now()
        
        if commit:
            location.save()
        return location


class FoodbankLocationAreaForm(forms.Form):
    name = forms.CharField(max_length=100, help_text="Name of the location")
    mapit_id = forms.IntegerField(help_text="MapIt Area ID")

   
class FoodbankDonationPointForm(ModelForm):
    class Meta:
        model = FoodbankDonationPoint
        fields = "__all__"
        widgets = {'foodbank': HiddenInput()}
        exclude = ('is_closed',)

    def save(self, commit=True): 
        donation_point = super().save(commit=False)
        donation_point.edited = datetime.now()
        
        if commit:
            donation_point.save()
        return donation_point


class FoodbankLocationPoliticsForm(ModelForm):
    class Meta:
        model = Foodbank
        fields = "__all__"


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
        if self["foodbank"].value():
            self.fields['need'].queryset = FoodbankChange.objects.filter(foodbank=self["foodbank"].value()).order_by('-created')
        else:
            self.fields['need'].queryset = FoodbankChange.objects.all().order_by('-created')


class OrderItemForm(ModelForm):
    class Meta:
        model = OrderItem
        fields = "__all__"


class SlugRedirectForm(ModelForm):
    class Meta:
        model = SlugRedirect
        fields = "__all__"


class OrderGroupForm(ModelForm):
    class Meta:
        model = OrderGroup
        fields = "__all__"


class NeedForm(ModelForm):
    foodbank = ModelChoiceField(queryset=Foodbank.objects.filter().order_by('name'), required=False)
    class Meta:
        model = FoodbankChange
        fields = "__all__"
        exclude = ('change_text_original', 'input_method', 'name', 'uri', 'distill_id', 'excess_change_text_original')


class NeedLineForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['type'].widget = HiddenInput()
        self.fields['item'].widget.attrs['class'] = "item"
        self.fields['category'].widget.attrs['class'] = "category"
    class Meta:
        model = FoodbankChangeLine
        fields = "__all__"

class ParliamentaryConstituencyForm(ModelForm):
    class Meta:
        model = ParliamentaryConstituency
        fields = "__all__"


class GfCredentialForm(ModelForm):
    class Meta:
        model = GfCredential
        fields = "__all__"


