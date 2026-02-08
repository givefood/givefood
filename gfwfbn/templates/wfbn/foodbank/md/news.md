# News - {{ foodbank.full_name }}

{% for article in foodbank.articles %}- [{{ article.title_captialised }}]({{ article.url }}) ({{ article.published_date }})
{% endfor %}
