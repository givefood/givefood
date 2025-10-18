from django.urls import path
from gfoffline.views import *

app_name = "gfoffline"

urlpatterns = (
    path("precacher/", precacher, name="precacher"),
    path("oc_geocode/", fire_oc_geocode, name="fire_oc_geocode"),
    path("discrepancy_check/", discrepancy_check, name="discrepancy_check"),
    path(
        "foodbank_need_check/<slug:slug>/",
        foodbank_need_check,
        name="foodbank_need_check"
    ),
    path("cleanup_subs/", cleanup_subs, name="cleanup_subs"),
    path("days_between_needs/", days_between_needs, name="days_between_needs"),
    path("pluscodes/", pluscodes, name="pluscodes"),
    path("place_ids/", place_ids, name="place_ids"),
    path("need_categorisation/", need_categorisation, name="need_categorisation"),
    path("load_mps/", load_mps, name="load_mps"),
    path("refresh_mps/", refresh_mps, name="refresh_mps"),
)
