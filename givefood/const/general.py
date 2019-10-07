DELIVERY_HOURS = [6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22]
DELIVERY_HOURS_CHOICES = tuple((hour, hour) for hour in DELIVERY_HOURS)

COUNTRIES = [
    "England",
    "Wales",
    "Scotland",
    "Northern Ireland",
]
COUNTRIES_CHOICES = tuple((country, country) for country in COUNTRIES)

DELIVERY_PROVIDERS = [
    "Tesco",
]
DELIVERY_PROVIDER_CHOICES = tuple((delivery_provider, delivery_provider) for delivery_provider in DELIVERY_PROVIDERS)

FOODBANK_NETWORKS = [
    "Trussell Trust",
    "Independent",
]
FOODBANK_NETWORK_CHOICES = tuple((network, network) for network in FOODBANK_NETWORKS)

PACKAGING_WEIGHT_PC = 1.12
