from django.conf.urls import include, url
from views import *

urlpatterns = (
    url(r'^$', index, name="index"),
    url(r'^foodbanks/$', foodbanks, name="foodbanks"),
    url(r'^foodbank/(?P<slug>[-\w]+)/$', foodbank, name="foodbank"),
)