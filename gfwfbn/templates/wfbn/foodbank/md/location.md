{% autoescape off %}# {{ location.name }} - {{ foodbank.full_name }}

{% if foodbank.is_closed %}**This food bank is closed.**

{% endif %}{% if foodbank.latest_need.change_text != "Unknown" and foodbank.latest_need.change_text != "Nothing" and foodbank.latest_need.change_text != "Facebook" %}## Items needed

{{ foodbank.latest_need.get_change_text }}
{% if foodbank.latest_need.excess_change_text %}
## Items not needed

{% for item in foodbank.latest_need.get_excess_text_list %}{{ item }}{% if not forloop.last %}, {% endif %}{% endfor %}
{% endif %}{% endif %}
{% if location.address or location.postcode %}
## Address

{% if location.address %}{{ location.address }}
{% endif %}{% if location.postcode %}{{ location.postcode }}{% endif %}
{% endif %}
{% if foodbank.delivery_address %}
## Delivery address

{{ foodbank.delivery_address }}
{% endif %}

## Contact

- Website: [{{ foodbank.url }}]({{ foodbank.url }})
{% if foodbank.phone_number %}- Phone: [{{ foodbank.phone_number }}](tel:{{ foodbank.phone_number }})
{% endif %}- Email: [{{ foodbank.contact_email }}](mailto:{{ foodbank.contact_email }})

## Parent food bank

[{{ foodbank.full_name }}]({% url 'wfbn-md:md_foodbank' foodbank.slug %})
{% endautoescape %}
