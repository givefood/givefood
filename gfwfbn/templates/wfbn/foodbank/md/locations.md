# Locations - {{ foodbank.full_name }}

## Main

{{ foodbank.address }}
{{ foodbank.postcode }}
{% if foodbank.delivery_address %}
## Delivery

{{ foodbank.delivery_address }}
{% endif %}
{% for location in foodbank.locations %}
## {{ location.name }}

{% if location.address %}{{ location.address }}
{% endif %}{% if location.postcode %}{{ location.postcode }}{% endif %}

[View details]({% url 'wfbn:foodbank_location' foodbank.slug location.slug %})
{% endfor %}
