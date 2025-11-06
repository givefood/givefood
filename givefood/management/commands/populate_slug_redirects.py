from django.core.management.base import BaseCommand
from django.core.cache import cache

from givefood.models import SlugRedirect


class Command(BaseCommand):

    help = 'Populate SlugRedirect table with food bank slug redirects'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing redirects before populating',
        )

    def handle(self, *args, **options):

        # Data from OLD_FOODBANK_SLUGS
        old_foodbank_slugs = {
            "angus": "dundee-angus",
            "dundee": "dundee-angus",
            "lifeshare": "lifeshare-manchester",
            "galashiels": "galashiels-and-area",
            "bristol-north": "north-bristol-south-gloucestershire",
            "feed": "st-albans-and-district",
            "hillingdon/hayes-st-anselm": "st-anselm",
            "b30": "b30-south-birmingham",
            "kingfisher": "north-solihull",
            "bethnal-green": "bow/bethnal-green",
            "swansea/st-thomas-church": "st-thomas",
            "skye": "skye-lochalsh",
            "cromer-district": "north-norfolk",
            "blandford": "nourish",
            "abergele-district/kinmel-bay-church": "kinmel-bay-church",
            "vauxhall": "lambeth-south-croydon",
            "ballymena/ballymena-north": "ballymena-north",
            "quinton-oldbury": "quinton",
            "chalk-farm": "kentish-town",
            "cupboard-love": "bridport",
            "glastonbury": "glastonbury-street",
            "hollingdean": "hollingdean-fiveways",
            "bay": "the-bay",
            "st-pauls-centre": ":st-pauls",
            "central-southwark-community-hub": "spring-community-hub",
            "clyde-avon-nethan": "larkhall-district",
            "norwood-brixton": "lambeth-south-croydon",
            "southbourne": "bournemouth/southbourne",
            "east-ayrshire": "ayrshire-east",
            "falkirk/donationpoint/asda-superstore-stenhousemuir": "klsb/donationpoint/asda-stenhousemuir",
            "newcastle-west-end": "newcastle",
            "kings-centre-honiton": "honiton",
            "helston-lizard": "helston-the-lizard",
            "restore-northampton": "northampton",
            "wells-vineyard": "wells",
            "lambeth-south-croydon": "lambeth-croydon",
            "ivybridge": "ivybridge-district",
            "waterloo": "lambeth-croydon",
            "lowestoft": "lowestoft-district",
            "skelmersdale": "skelmersdale-district",
            "keynsham": "bath-keynsham-somer-valley",
            "bath": "bath-keynsham-somer-valley",
            "somer-valley": "bath-keynsham-somer-valley",
            "stretford": "trafford-north",
            "durham": "county-durham",
            "hunstanton-and-district": "hunstanton-district",
            "redcar": "redcar-area",
            "cpr": "transformation",
            "belfast-south-west": "south-west-belfast",
            "yarmouth-magdalen": "great-yarmouth",
            "stow-park-community-centre": "newport-district",
            "godmanchester": "godmanchester-huntingdon",
        }

        if options['clear']:
            existing_count = SlugRedirect.objects.count()
            SlugRedirect.objects.all().delete()
            self.stdout.write(
                self.style.WARNING(
                    f'Deleted {existing_count} existing slug redirects'
                )
            )

        # Track statistics
        created_count = 0
        skipped_count = 0
        updated_count = 0

        for old_slug, new_slug in old_foodbank_slugs.items():
            # Check if redirect already exists
            try:
                redirect = SlugRedirect.objects.get(old_slug=old_slug)
                if redirect.new_slug != new_slug:
                    redirect.new_slug = new_slug
                    redirect.save()
                    updated_count += 1
                    self.stdout.write(
                        f'Updated: {old_slug} -> {new_slug}'
                    )
                else:
                    skipped_count += 1
            except SlugRedirect.DoesNotExist:
                SlugRedirect.objects.create(old_slug=old_slug, new_slug=new_slug)
                created_count += 1
                self.stdout.write(
                    f'Created: {old_slug} -> {new_slug}'
                )

        # Clear the cache
        cache.delete('slug_redirects_dict')
        self.stdout.write(
            self.style.WARNING('Cleared slug_redirects_dict cache')
        )

        # Summary
        self.stdout.write(
            self.style.SUCCESS(
                f'\nSummary:\n'
                f'  Created: {created_count}\n'
                f'  Updated: {updated_count}\n'
                f'  Skipped: {skipped_count}\n'
                f'  Total in database: {SlugRedirect.objects.count()}'
            )
        )
