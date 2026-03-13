import asyncio

from django.core.management.base import BaseCommand

from givefood.utils.ai import gemini_async
from givefood.models import Place

BATCH_SIZE = 10

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


def _build_prompt(place):
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


async def _fetch_population(place):
    """Fetch population for a single place asynchronously."""
    prompt = _build_prompt(place)
    response = await gemini_async(
        prompt = prompt,
        temperature = 0,
        response_schema = RESPONSE_SCHEMA,
        response_mime_type = "application/json",
    )
    return place, response["population"]


async def _fetch_batch(batch):
    """Fetch populations for a batch of places concurrently."""
    tasks = [_fetch_population(place) for place in batch]
    return await asyncio.gather(*tasks)


class Command(BaseCommand):

    help = 'Populate the population field for each Place using AI'

    def handle(self, *args, **options):

        places = Place.objects.filter(population__isnull=True).order_by("gbpnid")
        place_count = places.count()

        self.stdout.write(f"Found {place_count} places without population")

        place_list = list(places)
        processed = 0

        for i in range(0, len(place_list), BATCH_SIZE):
            batch = place_list[i:i + BATCH_SIZE]
            results = asyncio.run(_fetch_batch(batch))

            for place, population in results:
                place.population = population
                place.save()
                processed += 1
                self.stdout.write(f"{place.name}: {population} ({processed} of {place_count})")
