from django import forms
from django.forms import HiddenInput


to_from_attrs = {
    "readonly":"readonly",
}

class ConstituentDetailsForm(forms.Form):
    name = forms.CharField(label="Your Name", max_length=100, help_text="E.g. Amy Baker or Tom Smith")
    address = forms.CharField(label="Your Full Address", widget=forms.Textarea, help_text="Lay out the address using multiple lines and please include your postcode")
    email = forms.EmailField(label="Your Email Address", help_text="We'll send you a copy, and also hopefully needed so the candidate is able to respond")
    subscribe = forms.BooleanField(label="Keep me up to date with very occasional emails about helping food banks", initial=True, required=False)


class EmailForm(forms.Form):

    from_field = forms.CharField(label="From", max_length=200, widget=forms.TextInput(attrs=to_from_attrs))
    from_name = forms.CharField(max_length=100, widget=HiddenInput())
    from_email = forms.EmailField(max_length=100, widget=HiddenInput())

    to_field = forms.CharField(label="To", max_length=200, widget=forms.TextInput(attrs=to_from_attrs))

    subject = forms.CharField(label="Subject", max_length=200)
    body = forms.CharField(label="Email", widget=forms.Textarea)