from django.core.management.base import BaseCommand

from givefood.utils.ai import gemini
from givefood.models import Place


class Command(BaseCommand):

    help = 'Populate the population field for each Place using AI'

    def handle(self, *args, **options):

        places = Place.objects.filter(population__isnull=True)
        place_count = places.count()

        self.stdout.write(f"Found {place_count} places without population")

        the_counter = 1
        for place in places:

            prompt = (
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

            response_schema = {
                "type": "object",
                "properties": {
                    "population": {
                        "type": "integer",
                        "description": "The population of the place",
                    },
                },
                "required": ["population"],
            }

            response = gemini(
                prompt = prompt,
                temperature = 0,
                response_schema = response_schema,
                response_mime_type = "application/json",
            )

            population = response["population"]
            place.population = population
            place.save()

            self.stdout.write(f"{place.name}: {population} ({the_counter} of {place_count})")

            the_counter += 1
