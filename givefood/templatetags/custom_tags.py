from django import template
from givefood.func import get_image, make_friendly_phone, make_full_phone

register = template.Library()

@register.simple_tag
def product_image(delivery_provider, product_name):

    url = get_image(delivery_provider, product_name)
    return url

@register.filter
def friendly_phone(phone_number):
    return make_friendly_phone(phone_number)

@register.filter
def full_phone(phone_number):
    return make_full_phone(phone_number)