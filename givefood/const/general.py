DELIVERY_HOURS = [6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22]
DELIVERY_HOURS_CHOICES = tuple((hour, hour) for hour in DELIVERY_HOURS)

COUNTRIES = [
    "England",
    "Wales",
    "Scotland",
    "Northern Ireland",
    "Isle of Man",
    "Jersey",
    "Guernsey",
]
COUNTRIES_CHOICES = tuple((country, country) for country in COUNTRIES)

DELIVERY_PROVIDERS = [
    "Tesco",
    "Sainsbury's",
    "Costco",
    "Pedal Me",
]
DELIVERY_PROVIDER_CHOICES = tuple((delivery_provider, delivery_provider) for delivery_provider in DELIVERY_PROVIDERS)

FOODBANK_NETWORKS = [
    "Trussell Trust",
    "IFAN",
    "Independent",
]
FOODBANK_NETWORK_CHOICES = tuple((network, network) for network in FOODBANK_NETWORKS)

PACKAGING_WEIGHT_PC = 1.18

CHECK_COUNT_PER_DAY = {
    2019:5784,
    2020:7753,
}
PAGE_SIZE_PER_COUNT = 1444997 #Bytes

FB_MC_KEY = "all_foodbanks"
LOC_MC_KEY = "all_locations"
ITEMS_MC_KEY = "all_items"

RICK_ASTLEY = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

API_DOMAIN = "https://www.givefood.org.uk"
