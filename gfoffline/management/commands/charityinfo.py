from datetime import datetime

from django.core.management.base import BaseCommand

from givefood.func import foodbank_charity_crawl
from givefood.models import Foodbank, CrawlSet


class Command(BaseCommand):

    help = 'Crawl charity details for all food banks with charity numbers.'

    def handle(self, *args, **options):

        crawl_set = CrawlSet(
            crawl_type = "charity",
        )
        crawl_set.save()

        foodbanks = Foodbank.objects.filter(charity_number__isnull=False, is_closed=False).order_by("?")

        the_counter = 1
        foodbank_count = foodbanks.count()
        
        for foodbank in foodbanks:

            self.stdout.write(f"Check {foodbank.country} {foodbank.name} ({the_counter} of {foodbank_count})")

            foodbank_charity_crawl(foodbank, crawl_set)

            the_counter += 1

        crawl_set.finish = datetime.now()
        crawl_set.save()