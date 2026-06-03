from django.urls import path
from gfadmin.views import *

urlpatterns = [

    path("credentials/", credentials, name="credentials"),
    path("credentials/new/", credentials_form, name="credential_new"),
    path("credentials/decache/", credentials_decache, name="credentials_decache"),
    path("credential/delete/", delete_credential, name="credential_delete"),
    path("credential/<str:name>/", credential_detail, name="credential_detail"),

]
