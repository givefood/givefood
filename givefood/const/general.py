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

NEED_INPUT_TYPES = [
    "scrape",
    "user",
    "typed",
    "ai",
]
NEED_INPUT_TYPES_CHOICES = tuple((input_type, input_type) for input_type in NEED_INPUT_TYPES)

NEED_LINE_TYPES = [
    "need",
    "excess",
]
NEED_LINE_TYPES_CHOICES = tuple((line_type, line_type) for line_type in NEED_LINE_TYPES)

FOODBANK_NETWORKS = [
    "Trussell Trust",
    "IFAN",
    "Independent",
]
FOODBANK_NETWORK_CHOICES = tuple((network, network) for network in FOODBANK_NETWORKS)

DISCREPANCY_TYPES = [
    "postcode",
    "address",
    "phone",
    "email",
    "charity_number",
    "need",
    "website",
]
DISCREPANCY_TYPES_CHOICES = tuple((discrepancy_type, discrepancy_type) for discrepancy_type in DISCREPANCY_TYPES)

DISCREPANCY_STATUSES = [
    "New",
    "Done",
    "Invalid",
]
DISCREPANCY_STATUS_CHOICES = tuple((status, status) for status in DISCREPANCY_STATUSES)


DONATION_POINT_COMPANIES = [
    "Sainsbury's",
    "Tesco",
    "Asda",
    "Morrisons",
    "Waitrose",
    "Co-op",
    "Aldi",
    "Lidl",
    "Iceland",
    "Marks & Spencer",
    "Booths",
    "Budgens",
    "Costcutter",
    "Nisa",
    "Spar",
    "One Stop",
    "Premier",
    "McColl's",
    "Best-One",
    "Londis",
    "Mace",
    "Farmfoods",
    "Scotmid",
    "Eurospar",
]
DONATION_POINT_COMPANIES_CHOICES = tuple((company, company) for company in DONATION_POINT_COMPANIES)


TRUSSELL_TRUST_SCHEMA = {
    "@type": "NGO",
    "name": "Trussell Trust",
    "url": "https://www.trusselltrust.org",
    "email": "enquiries@trusselltrust.org",
    "telephone": "01722580180",
    "address": {
        "@type": "PostalAddress",
        "addressLocality": "Salisbury",
        "postalCode": "SP2 7HL",
        "streetAddress": "Unit 9 Ashfield Trading Estate, Ashfield Road"
    },
    "identifier": "1110522",
    "duns": "346282481",
    "sameAs":"https://en.wikipedia.org/wiki/The_Trussell_Trust",
}
IFAN_SCHEMA = {
    "@type": "NGO",
    "name": "IFAN",
    "url": "https://www.foodaidnetwork.org.uk",
    "email": "admin@foodaidnetwork.org.uk",
    "telephone": "07535389775",
    "address": {
        "@type": "PostalAddress",
        "addressLocality": "London",
        "postalCode": "WC2H 9JQ",
        "streetAddress": "71-75 Shelton Street"
    },
    "identifier": "1180382",
    "duns": "224810933",
    "sameAs": "https://en.wikipedia.org/wiki/Independent_Food_Aid_Network",
}

PACKAGING_WEIGHT_PC = 1.18

FB_MC_KEY = "all_foodbanks"
FB_OPEN_MC_KEY = "all_open_foodbanks"
LOC_MC_KEY = "all_locations"
LOC_OPEN_MC_KEY = "all_open_locations"
ITEMS_MC_KEY = "all_items"
PARLCON_MC_KEY = "all_parlcon"

RICK_ASTLEY = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

SITE_DOMAIN = "https://www.givefood.org.uk"
API_DOMAIN = SITE_DOMAIN

ENABLE_WRITE = True

OLD_FOODBANK_SLUGS = {
    "angus":"dundee-angus",
    "dundee":"dundee-angus",
    "lifeshare":"lifeshare-manchester",
    "galashiels":"galashiels-and-area",
    "bristol-north":"north-bristol-south-gloucestershire",
    "feed":"st-albans-and-district",
    "hillingdon/hayes-st-anselm":"st-anselm",
    "b30":"b30-south-birmingham",
    "kingfisher":"north-solihull",
    "bethnal-green":"bow/bethnal-green",
    "swansea/st-thomas-church":"st-thomas",
    "skye":"skye-lochalsh",
    "cromer-district":"north-norfolk",
    "blandford":"nourish",
    "abergele-district/kinmel-bay-church":"kinmel-bay-church",
    "vauxhall":"norwood-brixton/vauxhall",
    "ballymena/ballymena-north":"ballymena-north",
    "quinton-oldbury":"quinton",
    "chalk-farm":"kentish-town",
    "cupboard-love":"bridport",
    "glastonbury":"glastonbury-street",
    "hollingdean":"hollingdean-fiveways",
}

FOODBANK_SUBPAGES = [
    "locations",
    "news",
    "politics",
    "donationpoints",
    "socialmedia",
    "nearby",
    "history",
    "subscribe",
]

DONT_APPEND_FOOD_BANK = [
    "Salvation Army",
    "Oxford Food Hub",
    "Staffordshire Food and Furniture Bank",
    "The Shack Food Project",
    "Family Food Bank",
    "Adat Yeshua Foodbank",
    "New Hope Food Bank",
    "Felix Multibank",
]

POSTCODE_REGEX = "^(([A-Z]{1,2}[0-9][A-Z0-9]?|ASCN|STHL|TDCU|BBND|[BFS]IQQ|PCRN|TKCA) ?[0-9][A-Z]{2}|BFPO ?[0-9]{1,4}|(KY[0-9]|MSR|VG|AI)[ -]?[0-9]{4}|[A-Z]{2} ?[0-9]{2}|GE ?CX|GIR ?0A{2}|SAN ?TA1)$"