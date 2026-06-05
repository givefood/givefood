from django.core.management.base import BaseCommand

from givefood.utils.crawlers import do_foodbank_need_check_async
from givefood.models import Foodbank, CrawlSet


class Command(BaseCommand):

    help = 'Queues a need check for every food bank onto the "needcheck" queue.'

    def handle(self, *args, **options):

        self.stdout.write("Queuing need checks for all food banks...")

        crawl_set = CrawlSet(
            crawl_type = "need",
        )
        crawl_set.save()

        foodbanks = Foodbank.objects.exclude(is_closed = True).order_by("?")
        foodbank_count = foodbanks.count()

        for the_counter, foodbank in enumerate(foodbanks, start=1):
            do_foodbank_need_check_async.enqueue(foodbank.slug, crawl_set.id)
            self.stdout.write(f"Queued {foodbank.name} ({the_counter} of {foodbank_count})")

        self.stdout.write(
            f"Queued {foodbank_count} need check(s) on the 'needcheck' queue (crawl set {crawl_set.id})"
        )
