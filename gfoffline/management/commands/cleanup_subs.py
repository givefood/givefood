from datetime import datetime, timedelta

from django.core.management.base import BaseCommand

from givefood.models import FoodbankSubscriber


class Command(BaseCommand):

    help = 'Delete unconfirmed foodbank subscribers older than 28 days'

    def handle(self, *args, **options):

        unconfirmed_subscribers = FoodbankSubscriber.objects.filter(
            confirmed=False,
            created__lte=datetime.now() - timedelta(days=28),
        )

        subscriber_count = unconfirmed_subscribers.count()

        self.stdout.write(
            f"Found {subscriber_count} unconfirmed subscribers "
            f"older than 28 days"
        )

        deleted_count = 0
        for unconfirmed_subscriber in unconfirmed_subscribers:
            unconfirmed_subscriber.delete()
            deleted_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully deleted {deleted_count} unconfirmed subscribers'
            )
        )
