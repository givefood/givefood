{% load humanize %}# Give Food

We're a UK charity that uses data to highlight local and structural food insecurity then provides tools to help alleviate it.

Use our unique database to find a food bank near you, see what they need and how you can help by donating or volunteering.

## Recently updated

{% for foodbank in recently_updated %}- [{{ foodbank.foodbank_name }}]({{ SITE_DOMAIN }}{% url 'wfbn:foodbank' foodbank.foodbank_name_slug %})
{% endfor %}

## Most viewed this week

{% for foodbank in most_viewed %}- [{{ foodbank.name }}]({{ SITE_DOMAIN }}{% url 'wfbn:foodbank' foodbank.slug %})
{% endfor %}

## Statistics

- Food banks: {{ stats.foodbanks|intcomma:False }}
- Donation points: {{ stats.donationpoints|intcomma:False }}
- Items requested: {{ stats.items|intcomma:False }}
- Meals delivered: {{ stats.meals|intcomma:False }}

## Countries

- [England]({{ SITE_DOMAIN }}{% url 'country' 'england' %})
- [Scotland]({{ SITE_DOMAIN }}{% url 'country' 'scotland' %})
- [Wales]({{ SITE_DOMAIN }}{% url 'country' 'wales' %})
- [Northern Ireland]({{ SITE_DOMAIN }}{% url 'country' 'northern-ireland' %})

## Links

- [Find food banks]({{ SITE_DOMAIN }}{% url 'wfbn:index' %})
- [Donate]({{ SITE_DOMAIN }}{% url 'donate' %})
- [About us]({{ SITE_DOMAIN }}{% url 'about_us' %})
- [API]({{ SITE_DOMAIN }}/api/)
