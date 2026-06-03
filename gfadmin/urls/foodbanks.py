from django.urls import path
from gfadmin.views import *

urlpatterns = [

    path("foodbanks/", foodbanks, name="foodbanks"),
    path("foodbanks/next/", foodbanks_next, name="foodbanks_next"),
    path("foodbanks/dupe_postcodes/", foodbanks_dupe_postcodes, name="foodbanks_dupe_postcodes"),
    path("foodbanks/csv/", foodbanks_csv, name="foodbanks_csv"),
    path("foodbanks/without_need/", foodbanks_without_need, name="foodbanks_without_need"),

    path("foodbank/new/", foodbank_form, name="foodbank_new"),
    path("foodbank/<slug:slug>/", foodbank, name="foodbank"),
    path("foodbank/<slug:slug>/edit/", foodbank_form, name="foodbank_edit"),
    path("foodbank/<slug:slug>/check/", foodbank_check, name="foodbank_check"),
    path("foodbank/<slug:slug>/check/prompt/", foodbank_check_prompt, name="foodbank_check_prompt"),
    path("foodbank/<slug:slug>/check/result/", foodbank_check_result, name="foodbank_check_result"),

    path("foodbank/<slug:slug>/donationpoint/new/", donationpoint_form, name="donationpoint_new"),
    path("foodbank/<slug:slug>/donationpoint/<slug:dp_slug>/edit/", donationpoint_form, name="donationpoint_edit"),
    path("foodbank/<slug:slug>/donationpoint/<slug:dp_slug>/delete/", donationpoint_delete, name="donationpoint_delete"),

    path("foodbank/<slug:slug>/photo/<int:photo_id>/delete/", photo_delete, name="photo_delete"),

    path("foodbank/<slug:slug>/location/new/", fblocation_form, name="fblocation_new"),
    path("foodbank/<slug:slug>/location/new/area/", fblocation_area_form, name="fblocation_area_new"),
    path("foodbank/<slug:slug>/location/<slug:loc_slug>/edit/", fblocation_form, name="fblocation_edit"),
    path("foodbank/<slug:slug>/location/<slug:loc_slug>/delete/", fblocation_delete, name="fblocation_delete"),
    path("foodbank/<slug:slug>/location/<slug:loc_slug>/politics/edit/", fblocation_politics_edit, name="fblocation_politics_edit"),

    path("foodbank/<slug:slug>/politics/edit/", foodbank_politics_form, name="foodbank_politics_edit"),
    path("foodbank/<slug:slug>/edit/urls/", foodbank_urls_form, name="foodbank_urls_edit"),
    path("foodbank/<slug:slug>/edit/address/", foodbank_address_form, name="foodbank_address_edit"),
    path("foodbank/<slug:slug>/edit/phone/", foodbank_phone_form, name="foodbank_phone_edit"),
    path("foodbank/<slug:slug>/edit/email/", foodbank_email_form, name="foodbank_email_edit"),
    path("foodbank/<slug:slug>/edit/fsa-id/", foodbank_fsa_id_form, name="foodbank_fsa_id_edit"),
    path("foodbank/<slug:slug>/addsub/", foodbank_addsub, name="foodbank_addsub"),
    path("foodbank/<slug:slug>/crawl/", foodbank_crawl, name="foodbank_crawl"),
    path("foodbank/<slug:slug>/charity-crawl/", foodbank_charity_crawl, name="foodbank_charity_crawl"),
    path("foodbank/<slug:slug>/sendrfi/", foodbank_rfi, name="foodbank_rfi"),
    path("foodbank/<slug:slug>/resave/", foodbank_resave, name="foodbank_resave"),
    path("foodbank/<slug:slug>/touch/", foodbank_touch, name="foodbank_touch"),
    path("foodbank/<slug:slug>/use-ai/<str:field>/", foodbank_use_ai_detail, name="foodbank_use_ai_detail"),
    path("foodbank/<slug:slug>/delete/", foodbank_delete, name="foodbank_delete"),

    path("donationpoints/", donationpoints, name="donationpoints"),

]
