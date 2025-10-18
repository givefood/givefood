import logging
from django.apps import apps
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):

    help = (
        'Resave all instances of a specific model to trigger model save() '
        'methods and side effects.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            'model',
            type=str,
            help='Name of the model to resave '
                 '(e.g., Foodbank, FoodbankLocation)'
        )

    def handle(self, *args, **options):
        model_name = options['model']

        try:
            model_class = apps.get_model("givefood", model_name)
        except LookupError:
            raise CommandError(
                f'Model "{model_name}" does not exist in the givefood app'
            )

        instances = model_class.objects.all()
        instance_count = instances.count()

        self.stdout.write(
            f"Resaving {instance_count} instances of {model_name}..."
        )

        counter = 0
        for instance in instances:
            counter += 1
            logging.info(
                "Resaving %s %s (%d of %d)" % (
                    model_name, instance, counter, instance_count
                )
            )
            self.stdout.write(
                f"Resaving {model_name} {instance} "
                f"({counter} of {instance_count})"
            )
            instance.save()

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully resaved {instance_count} instances '
                f'of {model_name}'
            )
        )
