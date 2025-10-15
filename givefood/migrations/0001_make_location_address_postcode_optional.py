# Generated migration for making FoodbankLocation address and postcode optional

from django.db import migrations, models
import django.core.validators
from givefood.const.general import POSTCODE_REGEX


class Migration(migrations.Migration):

    dependencies = [
        # This will need to be updated when other migrations exist
    ]

    operations = [
        migrations.AlterField(
            model_name='foodbanklocation',
            name='address',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='foodbanklocation',
            name='postcode',
            field=models.CharField(
                blank=True, 
                max_length=9, 
                null=True, 
                validators=[
                    django.core.validators.RegexValidator(
                        code='invalid_postcode', 
                        message='Not a valid postcode', 
                        regex=POSTCODE_REGEX
                    )
                ]
            ),
        ),
    ]
