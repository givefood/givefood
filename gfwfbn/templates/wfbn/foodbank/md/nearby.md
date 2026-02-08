# Nearby - {{ foodbank.full_name }}

{% for location in nearby %}{% if location.type == "location" %}- [{{ location.name }}]({% url 'wfbn:foodbank_location' location.foodbank_slug location.slug %}) ({{ location.foodbank_name }}) - {{ location.distance_mi|floatformat:1 }}mi away
{% else %}- [{{ location.name }}]({% url 'wfbn:foodbank' location.foodbank_slug %}) - {{ location.distance_mi|floatformat:1 }}mi away
{% endif %}{% endfor %}
