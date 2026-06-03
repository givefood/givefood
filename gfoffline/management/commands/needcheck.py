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
        total_tokens = 0

        for foodbank in foodbanks:

            self.stdout.write(f"Check {foodbank.name} ({the_counter} of {foodbank_count})")

            start_time = time.perf_counter()

            # Keep the sweep going if a single food bank fails (e.g. a Gemini 503/deadline)
            # so one transient error can't abort the whole run.
            try:
                result = do_foodbank_need_check(foodbank, crawl_set)
            except Exception as e:
                failures.append(foodbank.name)
                self.stderr.write(f"Failed {foodbank.name}: {e!r}")
                self.stderr.write(traceback.format_exc())
            else:
                elapsed_time = time.perf_counter() - start_time
                result = result or {}
                tokens = result.get("total_tokens", 0)
                prompt_tokens = result.get("prompt_tokens", 0)
                output_tokens = result.get("output_tokens", 0)
                total_tokens += tokens
                self.stdout.write(
                    f"Done  {foodbank.name} ({elapsed_time:.2f} seconds, "
                    f"{tokens:,} tokens: {prompt_tokens:,} in / {output_tokens:,} out)"
                )

            the_counter += 1

        crawl_set.finish = timezone.now()
        crawl_set.save()

        self.stdout.write(f"Total tokens used: {total_tokens:,}")
        if failures:
            self.stdout.write(f"Completed with {len(failures)} failure(s): {', '.join(failures)}")
        else:
            self.stdout.write("Completed with no failures")