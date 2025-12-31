import time
from datetime import datetime

from django.core.management.base import BaseCommand

from givefood.func import do_foodbank_need_check
from givefood.models import Foodbank, CrawlSet


class Command(BaseCommand):

    help = 'Checks all food banks for updated needs and updates the database.'

    def handle(self, *args, **options):

        self.stdout.write("Crawling all food banks for needs...")

        crawl_set = CrawlSet(
            crawl_type = "need",
        )
        crawl_set.save()

        foodbanks = Foodbank.objects.exclude(is_closed = True).order_by("?")

        the_counter = 1
        foodbank_count = foodbanks.count()
        
        for foodbank in foodbanks:

            self.stdout.write(f"Check {foodbank.name} ({the_counter} of {foodbank_count})")

            start_time = time.perf_counter()

            do_foodbank_need_check(foodbank, crawl_set)

            end_time = time.perf_counter()
            elapsed_time = end_time - start_time
            self.stdout.write(f"Done  {foodbank.name} ({elapsed_time:.2f} seconds)")

            the_counter += 1

        crawl_set.finish = datetime.now()
        crawl_set.save()