from django.urls import path
from gfwrite.views import *

app_name = "gfwrite"

urlpatterns = (

    path("", index, name="index"),
    path("to/<slug:slug>/", constituency, name="constituency"),
    path("to/<slug:slug>/email/", email, name="email"),
    path("to/<slug:slug>/email/send/", send, name="send"),
    path("to/<slug:slug>/email/done/", done, name="done"),

)