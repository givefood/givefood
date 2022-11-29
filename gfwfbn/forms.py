from django.forms import Form, ModelForm, DateInput, ModelChoiceField, HiddenInput
from django import forms

from givefood.models import Foodbank, FoodbankChange, FoodbankLocation

class NeedForm(forms.ModelForm):

    class Meta:
        model = FoodbankChange
        fields = ("change_text","excess_change_text",)
        help_texts = {
            "change_text": "Items you need donated. Use a new line for each.",
            "excess_change_text": "Items that you have too many of. Again, use a new line for each.",
        }


class FoodbankLocationForm(forms.ModelForm):

    class Meta:
        model = Foodbank
        fields = ("address","postcode","country")


class LocationLocationForm(forms.ModelForm):

    class Meta:
        model = FoodbankLocation
        fields = ("address","postcode","phone_number","email")


class ContactForm(forms.ModelForm):

    class Meta:
        model = Foodbank
        fields = ("network","charity_number","facebook_page","twitter_handle","contact_email","phone_number","secondary_phone_number", "url", "shopping_list_url")
        help_texts = {
            "charity_number": "Charity Commission for England and Wales, Office of the Scottish Charity Regulator, or Charity Commission for Northern Ireland charity number",
            "facebook_page": "e.g. the 'GiveFoodOrgUK' part of facebook.com/GiveFoodOrgUK",
            "twitter_handle": "e.g. the 'GiveFoodCharity' part of twitter.com/GiveFoodCharity",
            "url": "Your web address",
            "shopping_list_url": "Web address where we can see a list of the items you are requesting",
        }