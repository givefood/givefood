import time
from datetime import datetime

from django.core.management.base import BaseCommand

from givefood.func import foodbank_article_crawl
from givefood.models import Foodbank, CrawlSet


class Command(BaseCommand):

    help = 'Runs a specific view function from the command line.'

    def handle(self, *args, **options):

        crawl_set = CrawlSet(
            crawl_type = "article",
        )
        crawl_set.save()

        foodbanks = Foodbank.objects.filter(rss_url__isnull=False).order_by("?")

        the_counter = 1
        foodbank_count = foodbanks.count()
        
        for foodbank in foodbanks:

            self.stdout.write(f"Check {foodbank.name} ({the_counter} of {foodbank_count})")
            start_time = time.perf_counter()

            foodbank_article_crawl(foodbank, crawl_set)

            end_time = time.perf_counter()
            elapsed_time = end_time - start_time
            self.stdout.write(f"Done  {foodbank.name} ({elapsed_time:.2f} seconds)")

            the_counter += 1

        crawl_set.finish = datetime.now()
        crawl_set.save()