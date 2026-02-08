{% autoescape off %}# Sitemap

## Pages

{% for url_name in url_names %}- [{{ url_name }}]({{ domain }}{% url url_name %})
{% endfor %}

## Countries

{% for country_slug in country_slugs %}- [{{ country_slug }}]({{ domain }}{% url 'country' country_slug %})
{% endfor %}

## Food Banks

{% for foodbank in foodbanks %}- [{{ foodbank.name }}]({% url 'wfbn-md:md_foodbank' foodbank.slug %})
{% endfor %}

## Locations

{% for location in locations %}- [{{ location.name }}]({% url 'wfbn-md:md_foodbank_location' location.foodbank_slug location.slug %})
{% endfor %}

## Donation Points

{% for donationpoint in donationpoints %}- [{{ donationpoint.name }}]({% url 'wfbn-md:md_foodbank_donationpoint' donationpoint.foodbank_slug donationpoint.slug %})
{% endfor %}

## Constituencies

{% for constituency in constituencies %}- [{{ constituency.name }}]({{ domain }}{% url 'wfbn:constituency' constituency.slug %})
{% endfor %}
{% endautoescape %}
