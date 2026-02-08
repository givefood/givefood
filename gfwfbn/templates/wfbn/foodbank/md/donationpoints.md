# Donation Points - {{ foodbank.full_name }}

{% if not foodbank.address_is_administrative %}## Main

{{ foodbank.address }}
{{ foodbank.postcode }}
{% endif %}{% if foodbank.delivery_address %}
## Delivery

{{ foodbank.delivery_address }}
{% endif %}
{% for donation_point in foodbank.donation_points %}- [{{ donation_point.name }}]({% url 'wfbn:foodbank_donationpoint' foodbank.slug donation_point.slug %}) - {{ donation_point.address }}, {{ donation_point.postcode }}
{% endfor %}
