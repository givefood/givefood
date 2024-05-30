from django.conf.urls import url
from gfwrite.views import *

app_name = "gfwrite"

urlpatterns = (

    url(r'^$', index, name="index"),
    url(r'^to/(?P<slug>[-\w]+)/$', constituency, name="constituency"),
    url(r'^to/(?P<slug>[-\w]+)/(?P<person_id>\d+)/$', candidate, name="candidate"),
    url(r'^to/(?P<slug>[-\w]+)/(?P<person_id>\d+)/email/$', email, name="email"),
    url(r'^to/(?P<slug>[-\w]+)/(?P<person_id>\d+)/email/send/$', send, name="send"),
    url(r'^to/(?P<slug>[-\w]+)/(?P<person_id>\d+)/email/done/$', done, name="done"),

)