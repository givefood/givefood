import time
import traceback

from django.core.management.base import BaseCommand
from django.utils import timezone

from givefood.utils.crawlers import do_foodbank_need_check
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
        failures = []

        for foodbank in foodbanks:

            self.stdout.write(f"Check {foodbank.name} ({the_counter} of {foodbank_count})")

            start_time = time.perf_counter()

            # Keep the sweep going if a single food bank fails (e.g. a Gemini 503/deadline)
            # so one transient error can't abort the whole run.
            try:
                do_foodbank_need_check(foodbank, crawl_set)
            except Exception as e:
                failures.append(foodbank.name)
                self.stderr.write(f"Failed {foodbank.name}: {e!r}")
                self.stderr.write(traceback.format_exc())
            else:
                end_time = time.perf_counter()
                elapsed_time = end_time - start_time
                self.stdout.write(f"Done  {foodbank.name} ({elapsed_time:.2f} seconds)")

            the_counter += 1

        crawl_set.finish = timezone.now()
        crawl_set.save()

        if failures:
            self.stdout.write(f"Completed with {len(failures)} failure(s): {', '.join(failures)}")
        else:
            self.stdout.write("Completed with no failures")