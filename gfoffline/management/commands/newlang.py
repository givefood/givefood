from django.core.management.base import BaseCommand, CommandError

from givefood.func import translate_need_async
from givefood.models import Foodbank
from givefood.settings import LANGUAGES


class Command(BaseCommand):

    help = 'Translates the latest_need for all Foodbanks to a specified language'

    def add_arguments(self, parser):
        parser.add_argument(
            'language_code',
            type=str,
            help='Two-character language code (e.g., pl, es, cy)'
        )

    def handle(self, *args, **options):
        language_code = options['language_code']

        # Validate language code is 2 characters
        if len(language_code) != 2:
            raise CommandError('Language code must be exactly 2 characters')

        # Validate language code is supported
        supported_languages = [lang[0] for lang in LANGUAGES]
        if language_code not in supported_languages:
            raise CommandError(
                f'Language code "{language_code}" is not supported. '
                f'Supported languages: {", ".join(supported_languages)}'
            )

        foodbanks = list(Foodbank.objects.all())
        foodbank_count = len(foodbanks)

        self.stdout.write(
            f"Starting translation of latest needs to '{language_code}' "
            f"for {foodbank_count} foodbanks..."
        )

        counter = 0
        translated_count = 0
        skipped_count = 0

        for foodbank in foodbanks:
            counter += 1

            # Log progress for every 100 foodbanks or key milestones
            if counter % 100 == 0 or counter == 1 or counter == foodbank_count:
                self.stdout.write(
                    f"Processing {foodbank.name} ({counter} of {foodbank_count})"
                )

            # Check if foodbank has a latest_need
            if foodbank.latest_need and foodbank.latest_need.need_id_str:
                # Translate the need asynchronously
                translate_need_async(language_code, foodbank.latest_need.need_id_str)
                translated_count += 1
            else:
                skipped_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully queued translation for {translated_count} needs. '
                f'Skipped {skipped_count} foodbanks without needs.'
            )
        )
