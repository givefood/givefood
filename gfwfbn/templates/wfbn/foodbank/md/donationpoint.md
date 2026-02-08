{% autoescape off %}# {{ donationpoint.name }} - {{ foodbank.full_name }}

{{ donationpoint.name }} is a donation point for [{{ foodbank.full_name }}]({% url 'wfbn-md:md_foodbank' foodbank.slug %}).

{% if has_need %}## Items needed

{{ foodbank.latest_need.get_change_text }}
{% if foodbank.latest_need.excess_change_text %}
## Items not needed

{% for item in foodbank.latest_need.get_excess_text_list %}{{ item }}{% if not forloop.last %}, {% endif %}{% endfor %}
{% endif %}{% endif %}
{% if donationpoint.opening_hours %}## Opening hours

{{ donationpoint.opening_hours }}
{% endif %}
{% if donationpoint.notes %}## Notes

{{ donationpoint.notes }}
{% endif %}

## Address

{{ donationpoint.address }}
{{ donationpoint.postcode }}
{{ donationpoint.country }}

## Contact

{% if donationpoint.url %}- Website: [{{ donationpoint.url }}]({{ donationpoint.url }})
{% endif %}{% if donationpoint.phone_number %}- Phone: [{{ donationpoint.phone_number }}](tel:{{ donationpoint.phone_number }})
{% endif %}
{% endautoescape %}
