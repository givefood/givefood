from django import template
from givefood.func import get_image

register = template.Library()

@register.simple_tag
def product_image(delivery_provider, product_name):

    url = get_image(delivery_provider, product_name)
    return url
