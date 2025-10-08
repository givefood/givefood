# Generated migration to rename latt_long fields to lat_lng

from django.db import migrations


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        # Rename Foodbank fields
        migrations.RenameField(
            model_name='Foodbank',
            old_name='latt_long',
            new_name='lat_lng',
        ),
        migrations.RenameField(
            model_name='Foodbank',
            old_name='delivery_latt_long',
            new_name='delivery_lat_lng',
        ),
        # Rename FoodbankLocation field
        migrations.RenameField(
            model_name='FoodbankLocation',
            old_name='latt_long',
            new_name='lat_lng',
        ),
        # Rename FoodbankDonationPoint field
        migrations.RenameField(
            model_name='FoodbankDonationPoint',
            old_name='latt_long',
            new_name='lat_lng',
        ),
        # Rename Place field
        migrations.RenameField(
            model_name='Place',
            old_name='latt_long',
            new_name='lat_lng',
        ),
    ]
