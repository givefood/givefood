from django.contrib import admin

# DJANGAE
from djangae.contrib.gauth.sql.models import GaeUser

admin.site.register(GaeUser)
