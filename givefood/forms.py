from django.utils import timezone

from django.forms import ModelForm, DateInput, ModelChoiceField, HiddenInput
from django import forms
from givefood.models import FoodbankDonationPoint, OrderGroup, Foodbank, Order, FoodbankChange, FoodbankLocation, ParliamentaryConstituency, OrderItem, GfCredential, FoodbankChangeLine, SlugRedirect, Place
from givefood.const.general import COUNTRIES_CHOICES, FOODBANK_NETWORK_CHOICES


# A fields = "__all__" form takes its order from the model, and the model takes its order from
# the order the fields were declared in. Foodbank, FoodbankLocation and FoodbankDonationPoint now
# inherit their address and location fields from the PhysicalPlace abstract base, which is
# declared in models/base.py, so those fields sort ahead of the ones declared on the model itself
# and the forms opened with address, postcode, lat_lng and place_id.
#
# These pin the order each form has always had. A field added to the model but missing here still
# appears on the form, at the end.
FOODBANK_FIELD_ORDER = [
    "name", "alt_name", "address", "postcode", "country", "lat_lng", "place_id",
    "delivery_address", "network", "network_id", "notes", "charity_number",
    "charity_just_foodbank", "facebook_page", "bankuet_slug", "fsa_id", "contact_email",
    "notification_email", "phone_number", "secondary_phone_number", "delivery_phone_number",
    "url", "shopping_list_url", "rss_url", "news_url", "donation_points_url", "locations_url",
    "contacts_url", "address_is_administrative", "is_closed", "is_school",
]

FOODBANK_LOCATION_FIELD_ORDER = [
    "foodbank", "name", "address", "postcode", "is_donation_point", "is_mobile", "lat_lng",
    "boundary_geojson", "place_id", "phone_number", "email",
]

FOODBANK_DONATION_POINT_FIELD_ORDER = [
    "foodbank", "name", "address", "postcode", "phone_number", "opening_hours",
    "wheelchair_accessible", "url", "in_store_only", "company", "store_id", "notes", "lat_lng",
    "place_id",
]


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


class FlagForm(forms.Form):
    our_page = forms.URLField(help_text="Address of the page you're flagging")
    your_email = forms.EmailField(help_text="Optional. Your email address", required=False)
    explanation = forms.CharField(widget=forms.Textarea, help_text="Optional. Please explain why you're flagging this page", required=False)


class FoodbankForm(ModelForm):
    field_order = FOODBANK_FIELD_ORDER
    class Meta:
        model = Foodbank
        fields = "__all__"

    def save(self, commit=True): 
        foodbank = super().save(commit=False)
        foodbank.edited = timezone.now()
        
        if commit:
            foodbank.save()
        return foodbank


class FoodbankUrlsForm(ModelForm):
    class Meta:
        model = Foodbank
        fields = ["url", "shopping_list_url", "rss_url", "news_url", "donation_points_url", "locations_url", "contacts_url"]

    def save(self, commit=True): 
        foodbank = super().save(commit=False)
        foodbank.edited = timezone.now()
        
        if commit:
            foodbank.save()
        return foodbank


class FoodbankAddressForm(ModelForm):
    class Meta:
        model = Foodbank
        fields = ["address", "postcode", "lat_lng", "place_id"]

    def save(self, commit=True): 
        foodbank = super().save(commit=False)
        foodbank.edited = timezone.now()
        
        if commit:
            foodbank.save()
        return foodbank


class FoodbankPhoneForm(ModelForm):
    class Meta:
        model = Foodbank
        fields = ["phone_number", "secondary_phone_number", "delivery_phone_number"]

    def save(self, commit=True): 
        foodbank = super().save(commit=False)
        foodbank.edited = timezone.now()
        
        if commit:
            foodbank.save()
        return foodbank


class FoodbankEmailForm(ModelForm):
    class Meta:
        model = Foodbank
        fields = ["contact_email", "notification_email"]

    def save(self, commit=True): 
        foodbank = super().save(commit=False)
        foodbank.edited = timezone.now()
        
        if commit:
            foodbank.save()
        return foodbank


class FoodbankFsaIdForm(ModelForm):
    class Meta:
        model = Foodbank
        fields = ["fsa_id"]

    def save(self, commit=True): 
        foodbank = super().save(commit=False)
        foodbank.edited = timezone.now()
        
        if commit:
            foodbank.save()
        return foodbank


class FoodbankPoliticsForm(ModelForm):
    field_order = FOODBANK_FIELD_ORDER
    class Meta:
        model = Foodbank
        fields = "__all__"


class FoodbankLocationForm(ModelForm):
    field_order = FOODBANK_LOCATION_FIELD_ORDER
    class Meta:
        model = FoodbankLocation
        fields = "__all__"
        widgets = {'foodbank': HiddenInput()}
        exclude = ('is_closed',)

    def save(self, commit=True): 
        location = super().save(commit=False)
        location.edited = timezone.now()
        
        if commit:
            location.save()
        return location


class FoodbankLocationAreaForm(forms.Form):
    name = forms.CharField(max_length=100, help_text="Name of the location")
    mapit_id = forms.IntegerField(help_text="MapIt Area ID")

   
class FoodbankDonationPointForm(ModelForm):
    field_order = FOODBANK_DONATION_POINT_FIELD_ORDER
    class Meta:
        model = FoodbankDonationPoint
        fields = "__all__"
        widgets = {'foodbank': HiddenInput()}
        exclude = ('is_closed',)

    def save(self, commit=True): 
        donation_point = super().save(commit=False)
        donation_point.edited = timezone.now()
        
        if commit:
            donation_point.save()
        return donation_point


class FoodbankLocationPoliticsForm(ModelForm):
    field_order = FOODBANK_FIELD_ORDER
    class Meta:
        model = Foodbank
        fields = "__all__"


class OrderForm(ModelForm):
    foodbank = ModelChoiceField(queryset=Foodbank.objects.filter(is_closed = False).order_by('name'), required=False)
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


class PlaceForm(ModelForm):
    class Meta:
        model = Place
        fields = "__all__"


