from django.urls import path
from gfadmin.views import *

urlpatterns = [

    path("needs/", needs, name="needs"),
    path("needs/deleteall/", needs_deleteall, name="needs_deleteall"),
    path("needs/csv/", needs_csv, name="needs_csv"),

    path("need/new", need_form, name="newneed"),
    path("need/<uuid:id>/", need, name="need"),
    path("need/<uuid:id>/edit/", need_form, name="need_form"),
    path("need/<uuid:id>/nonpertinent/", need_nonpertinent, name="need_nonpertinent"),
    path("need/<uuid:id>/delete/", need_delete, name="need_delete"),
    path("need/<uuid:id>/notifications/", need_notifications, name="need_notifications"),
    path("need/<uuid:id>/translations/", need_translations, name="need_translations"),
    path("need/<uuid:id>/email/", need_email, name="need_email"),
    path("need/<uuid:id>/categorise/", need_categorise, name="need_categorise"),
    path("need/<uuid:id>/<slug:action>/", need_publish, name="need_publish"),

    path("discrepancy/<slug:id>/", discrepancy, name="discrepancy"),
    path("discrepancy/<slug:id>/action/", discrepancy_action, name="discrepancy_action"),

]
