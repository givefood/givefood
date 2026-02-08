{% load humanize %}# Charity - {{ foodbank.full_name }}

{% if foodbank.charity_just_foodbank %}{{ foodbank.full_name }} is a registered charity.{% else %}{{ foodbank.full_name }} operates under a registered charity.{% endif %}

- Charity name: {{ foodbank.charity_name|title }}
- Charity number: {{ foodbank.charity_number }}
{% if foodbank.charity_type %}- Charity type: {{ foodbank.charity_type }}
{% endif %}{% if foodbank.charity_reg_date %}- Registration date: {{ foodbank.charity_reg_date|date:'jS F Y' }}
{% endif %}
{% if foodbank.charity_objectives %}## Objectives

{{ foodbank.charity_objectives }}
{% endif %}
{% if foodbank.charity_purpose %}## Purposes

{% for purpose in foodbank.charity_purpose_list %}- {{ purpose }}
{% endfor %}{% endif %}
{% if charity_years %}## Income & Expenditure

| Year | Income | Expenditure |
|------|--------|-------------|
{% for year in charity_years %}| {{ year.date|date:"Y" }} | £{{ year.income|intcomma }} | £{{ year.expenditure|intcomma }} |
{% endfor %}{% endif %}
