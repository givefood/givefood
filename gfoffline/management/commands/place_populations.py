import asyncio

from django.core.management.base import BaseCommand

from givefood.utils.ai import gemini_async
from givefood.models import Place

BATCH_SIZE = 10


def build_prompt(place):
    """Build the population prompt for a place."""
    return (
        "What is the population of this place in the United Kingdom? "
        "Estimate if you are not sure.\n\n"
        f"Name: {place.name}\n"
        f"Latitude, Longitude: {place.lat_lng}\n"
        f"Historic County: {place.histcounty}\n"
        f"Administrative County: {place.adcounty}\n"
        f"District: {place.district}\n"
        f"Unitary Authority: {place.uniauth}\n"
        f"Police Area: {place.police}\n"
        f"Region: {place.region}\n"
        f"Type: {place.type}\n"
        f"County: {place.county}\n"
    )


RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "population": {
            "type": "integer",
            "description": "The population of the place",
        },
    },
    "required": ["population"],
}


async def fetch_population(place):
    """Fetch the population for a single place via Gemini async."""
    prompt = build_prompt(place)
    response = await gemini_async(
        prompt = prompt,
        temperature = 0,
        response_schema = RESPONSE_SCHEMA,
        response_mime_type = "application/json",
    )
    return place, response["population"]


async def fetch_batch(batch):
    """Fetch populations for a batch of places concurrently."""
    return await asyncio.gather(*(fetch_population(place) for place in batch))


class Command(BaseCommand):

    help = 'Populate the population field for each Place using AI'

    def handle(self, *args, **options):

        places = list(Place.objects.filter(population__isnull=True).order_by("gbpnid"))
        place_count = len(places)

        self.stdout.write(f"Found {place_count} places without population")

        the_counter = 0
        for i in range(0, place_count, BATCH_SIZE):
            batch = places[i:i + BATCH_SIZE]
            results = asyncio.run(fetch_batch(batch))
            for place, population in results:
                the_counter += 1
                place.population = population
                place.save()
                self.stdout.write(f"{place.name}: {population} ({the_counter} of {place_count})")
