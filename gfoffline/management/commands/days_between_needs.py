from datetime import datetime

from django.core.management.base import BaseCommand

from givefood.func import get_all_open_foodbanks
from givefood.models import FoodbankChange


class Command(BaseCommand):

    help = 'Calculate and update the days_between_needs field for all open foodbanks.'

    def handle(self, *args, **options):

        number_of_needs = 5
        foodbanks = get_all_open_foodbanks()
        foodbank_count = foodbanks.count()

        self.stdout.write(f"Processing {foodbank_count} foodbanks...")

        counter = 0
        for foodbank in foodbanks:
            counter += 1

            days_between_needs = 0

            needs = FoodbankChange.objects.filter(foodbank=foodbank).order_by("-created")[:number_of_needs]
            if len(needs) == number_of_needs:
                last_need_date = needs[number_of_needs-1].created
                days_since_earliest_sample_need = (last_need_date - datetime.now()).days
                days_between_needs = int(-days_since_earliest_sample_need / number_of_needs)

            foodbank.days_between_needs = days_between_needs
            foodbank.save(do_decache=False, do_geoupdate=False)

            # Log progress for every 100 foodbanks or key milestones
            if counter % 100 == 0 or counter == 1 or counter == foodbank_count:
                self.stdout.write(
                    f"Processed {foodbank.name} "
                    f"({counter} of {foodbank_count})"
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully updated days_between_needs for {foodbank_count} foodbanks'
            )
        )
