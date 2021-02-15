from django.contrib import admin

# DJANGAE
from djangae.contrib.gauth_datastore.models import (
    GaeDatastoreUser,
    Group
)


@admin.register(GaeDatastoreUser)
class UserAdmin(admin.ModelAdmin):
    exclude = ('password',)

    def save_model(self, request, user, form, change):
        if not user.password:
            user.set_password(None)
        user.save()

admin.site.register(Group)
