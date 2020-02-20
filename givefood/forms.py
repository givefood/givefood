from django.forms import ModelForm, DateInput, ModelChoiceField, HiddenInput

from models import Foodbank, Order, FoodbankChange, FoodbankLocation


class FoodbankForm(ModelForm):
    class Meta:
        model = Foodbank
        fields = "__all__"
        exclude = ("parliamentary_constituency", "county", "district", "ward", "mp", "mp_party",)


class FoodbankPoliticsForm(ModelForm):
    class Meta:
        model = Foodbank
        fields = ("parliamentary_constituency", "county", "district", "ward", "mp", "mp_party",)


class FoodbankLocationForm(ModelForm):
    class Meta:
        model = FoodbankLocation
        fields = "__all__"
        widgets = {'foodbank': HiddenInput()}


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
