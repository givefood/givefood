# {{ foodbank.full_name }}

{% if foodbank.is_closed %}**This food bank is closed.**

{% endif %}{% if foodbank.latest_need.change_text != "Unknown" and foodbank.latest_need.change_text != "Nothing" and foodbank.latest_need.change_text != "Facebook" %}## Items needed

{{ foodbank.latest_need.get_change_text }}
{% if foodbank.latest_need.excess_change_text %}
## Items not needed

{% for item in foodbank.latest_need.get_excess_text_list %}{{ item }}{% if not forloop.last %}, {% endif %}{% endfor %}
{% endif %}{% endif %}

## Address

{{ foodbank.address }}
{{ foodbank.postcode }}
{{ foodbank.country }}
{% if foodbank.delivery_address %}
## Delivery address

{{ foodbank.delivery_address }}
{% endif %}

## Contact

- Website: {{ foodbank.url }}
{% if foodbank.phone_number %}- Phone: {{ foodbank.phone_number }}
{% endif %}{% if foodbank.secondary_phone_number %}- Phone: {{ foodbank.secondary_phone_number }}
{% endif %}- Email: {{ foodbank.contact_email }}

## Links

- [Locations]({% url 'wfbn:foodbank_locations' foodbank.slug %})
- [Donation points]({% url 'wfbn:foodbank_donationpoints' foodbank.slug %})
- [News]({% url 'wfbn:foodbank_news' foodbank.slug %})
- [Charity]({% url 'wfbn:foodbank_charity' foodbank.slug %})
- [Nearby]({% url 'wfbn:foodbank_nearby' foodbank.slug %})
