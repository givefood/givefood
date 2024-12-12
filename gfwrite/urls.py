from django.urls import re_path
from gfwrite.views import *

app_name = "gfwrite"

urlpatterns = (

    re_path(r'^$', index, name="index"),
    re_path(r'^to/(?P<slug>[-\w]+)/$', constituency, name="constituency"),
    re_path(r'^to/(?P<slug>[-\w]+)/email/$', email, name="email"),
    re_path(r'^to/(?P<slug>[-\w]+)/email/send/$', send, name="send"),
    re_path(r'^to/(?P<slug>[-\w]+)/email/done/$', done, name="done"),

)