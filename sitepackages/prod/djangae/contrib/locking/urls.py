# THIRD PARTY
from django.conf.urls import patterns, url

# DJANGAE
from .views import cleanup_locks


urlpatterns = patterns('',
    url(r'^djangae-cleanup-locks/$', cleanup_locks, name="cleanup_locks"),
)
