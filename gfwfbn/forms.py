from django.forms import Form, ModelForm, DateInput, ModelChoiceField, HiddenInput
from django import forms

from givefood.models import Foodbank, FoodbankChange, FoodbankLocation

class NeedForm(forms.ModelForm):

    class Meta:
        model = FoodbankChange
        fields = ("change_text",)


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
        fields = ("network","charity_number","facebook_page","twitter_handle","bankuet_slug","contact_email","phone_number","secondary_phone_number", "url", "shopping_list_url")