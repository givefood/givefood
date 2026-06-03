from django.urls import path
from gfadmin.views import *

urlpatterns = [

    path("emailtester/", email_tester, name="email_tester"),
    path("emailtester/test/", email_tester_test, name="email_tester_test"),
    path("webpushtester/", webpush_tester, name="webpush_tester"),
    path("webpushtester/send/", webpush_tester_send, name="webpush_tester_send"),
    path("whatsapptester/", whatsapp_tester, name="whatsapp_tester"),
    path("whatsapptester/send/", whatsapp_tester_send, name="whatsapp_tester_send"),

    path("needtestbed/", needtestbed, name="needtestbed"),

]
