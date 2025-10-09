import uuid
from django.core.management.base import BaseCommand
from givefood.models import FoodbankChange


class Command(BaseCommand):

    help = 'Regenerates all need_ids using UUID'

    def handle(self, *args, **options):

        needs = FoodbankChange.objects.all()
        total_count = needs.count()
        
        self.stdout.write(f"Regenerating need_ids for {total_count} needs...")
        
        updated_count = 0
        for need in needs:
            # Generate new UUID-based need_id
            # new_need_id = uuid.uuid4()
            
            # Update without triggering auto_now on modified field
            # Using queryset.update() to bypass model save() and auto_now
            FoodbankChange.objects.filter(pk=need.pk).update(need_id_str=str(need.need_id))
            
            updated_count += 1
            if updated_count % 100 == 0:
                self.stdout.write(f"Updated {updated_count}/{total_count}...")
        
        self.stdout.write(self.style.SUCCESS(f"Successfully regenerated {updated_count} need_ids"))
