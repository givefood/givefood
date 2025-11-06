from django import template
from givefood.func import make_friendly_phone, make_full_phone, make_url_friendly

register = template.Library()

@register.filter
def friendly_phone(phone_number):
    return make_friendly_phone(phone_number)

@register.filter
def full_phone(phone_number):
    return make_full_phone(phone_number)

@register.filter
def friendly_url(url):
    if url:
        return make_url_friendly(url)
    return None