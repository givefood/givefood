import logging

from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseRedirect, HttpResponse, HttpResponseForbidden, Http404
from django.db import IntegrityError
from django.template import RequestContext
from django.views.decorators.cache import cache_page
from django.template.defaultfilters import slugify
from django.core.urlresolvers import reverse
from django.views.decorators.csrf import csrf_exempt
from django.core.validators import validate_email
from django import forms

from google.appengine.api import urlfetch
from session_csrf import anonymous_csrf

from givefood.models import Foodbank, FoodbankLocation, ParliamentaryConstituency, FoodbankChange, FoodbankSubscriber
from givefood.func import get_all_constituencies, get_all_foodbanks, get_all_locations, find_foodbanks, geocode, find_locations, admin_regions_from_postcode, get_cred, send_email, post_to_email
from gfwfbn.forms import NeedForm, ContactForm, FoodbankLocationForm, LocationLocationForm


@cache_page(60*10)
def public_what_food_banks_need(request):

    headless = request.GET.get("headless", False)
    where_from = request.GET.get("from", False)
    address = request.GET.get("address", "")
    lattlong = request.GET.get("lat_lng", "")
    
    location_results = []

    if where_from != "trusselltrust":

        if address and not lattlong:
            lattlong = geocode(address)

        if lattlong:
            location_results = find_locations(lattlong, 10)

            for location in location_results:
                location_need = FoodbankChange.objects.filter(foodbank_name=location.get("foodbank_name"), published=True).latest("created")
                location["needs"] = location_need.change_text

    gmap_key = get_cred("gmap_key")

    template_vars = {
        "headless":headless,
        "where_from":where_from,
        "address":address,
        "lattlong":lattlong,
        "gmap_key":gmap_key,
        "location_results":location_results,
    }
    return render(request, "wfbn_index.html", template_vars)


def public_what_food_banks_need_click(request, slug):

    foodbank = get_object_or_404(Foodbank, slug = slug)
    utm_querystring = "?utm_source=givefood_org_uk&utm_medium=search&utm_campaign=needs"
    redirect_url = "%s%s" % (
        foodbank.shopping_list_url,
        utm_querystring,
    )
    return redirect(redirect_url)


@cache_page(60*10)
def public_wfbn_foodbank(request, slug):

    foodbank = get_object_or_404(Foodbank, slug = slug)
    nearby_locations = find_locations(foodbank.latt_long, 10, True)

    template_vars = {
        "foodbank":foodbank,
        "nearby_locations":nearby_locations,
    }

    return render(request, "wfbn_foodbank.html", template_vars)


@cache_page(60*30)
def public_wfbn_foodbank_map(request, slug):

    foodbank = get_object_or_404(Foodbank, slug = slug)
    gmap_static_key = get_cred("gmap_static_key")

    markers = "%s|" % foodbank.latt_long
    for location in foodbank.locations():
        markers = "%s%s|" % (markers, location.latt_long)

    if foodbank.name == "Salvation Army":
        markers = "&zoom=15"

    url = "https://maps.googleapis.com/maps/api/staticmap?center=%s&size=400x400&maptype=roadmap&format=png&visual_refresh=true&key=%s&markers=%s" % (foodbank.latt_long, gmap_static_key, markers)

    result = urlfetch.fetch(url)
    return HttpResponse(result.content, content_type='image/png')

@cache_page(60*10)
def public_wfbn_foodbank_history(request, slug):

    foodbank = get_object_or_404(Foodbank, slug = slug)
    needs = FoodbankChange.objects.filter(foodbank = foodbank, published = True).order_by("-created")[:25]

    template_vars = {
        "foodbank":foodbank,
        "needs":needs,
    }

    return render(request, "wfbn_foodbank_history.html", template_vars)


@cache_page(60*10)
def public_wfbn_foodbank_location(request, slug, locslug):

    foodbank = get_object_or_404(Foodbank, slug = slug)
    location = get_object_or_404(FoodbankLocation, slug = locslug, foodbank = foodbank)

    nearby_locations = find_locations(location.latt_long, 10, True)

    template_vars = {
        "foodbank":foodbank,
        "location":location,
        "nearby_locations":nearby_locations,
    }

    return render(request, "wfbn_foodbank_location.html", template_vars)


@cache_page(60*30)
def public_wfbn_foodbank_location_map(request, slug, locslug):

    foodbank = get_object_or_404(Foodbank, slug = slug)
    location = get_object_or_404(FoodbankLocation, slug = locslug, foodbank = foodbank)
    gmap_static_key = get_cred("gmap_static_key")

    result = urlfetch.fetch("https://maps.googleapis.com/maps/api/staticmap?center=%s&zoom=15&size=300x300&maptype=roadmap&format=png&visual_refresh=true&key=%s" % (location.latt_long, gmap_static_key))

    return HttpResponse(result.content, content_type='image/png')


@cache_page(60*5)
def public_wfbn_constituencies(request):

    postcode = request.GET.get("postcode", None)
    if postcode:
        admin_regions = admin_regions_from_postcode(postcode)
        parl_con = admin_regions.get("parliamentary_constituency", None)
        if parl_con:
            return HttpResponseRedirect(reverse("public_wfbn_constituency", kwargs={"slug":slugify(parl_con)}))

    constituencies = get_all_constituencies()

    template_vars = {
        "constituencies":constituencies,
    }

    return render(request, "wfbn_constituencies.html", template_vars)


@cache_page(60*5)
def public_wfbn_constituency(request, slug):

    if slug == "none":
        raise Http404

    foodbanks = Foodbank.objects.filter(parliamentary_constituency_slug = slug)
    locations = FoodbankLocation.objects.filter(parliamentary_constituency_slug = slug)

    constituency_foodbanks = []

    for foodbank in foodbanks:
        constituency_foodbanks.append({
            "name":foodbank.name,
            "slug":foodbank.slug,
            "constituency_name":foodbank.parliamentary_constituency,
            "mp":foodbank.mp,
            "mp_party":foodbank.mp_party,
            "mp_parl_id":foodbank.mp_parl_id,
            "latt_long":foodbank.latt_long,
            "needs":foodbank.latest_need(),
            "gmap_key":get_cred("gmap_key"),
            "url":"/needs/at/%s/" % (foodbank.slug)
        })

    for location in locations:
        constituency_foodbanks.append({
            "name":location.foodbank_name,
            "slug":location.foodbank_slug,
            "constituency_name":location.parliamentary_constituency,
            "mp":location.mp,
            "mp_party":location.mp_party,
            "mp_parl_id":location.mp_parl_id,
            "latt_long":location.latt_long,
            "needs":location.latest_need(),
            "url":"/needs/at/%s/%s/" % (location.foodbank_slug, location.slug)
        })

    #Dedupe
    constituency_locations = constituency_foodbanks
    constituency_foodbanks = {v['name']:v for v in constituency_foodbanks}.values()

    if not constituency_foodbanks:
        raise Http404

    constituency_name = constituency_foodbanks[0].get("constituency_name")
    mp = constituency_foodbanks[0].get("mp")
    mp_party = constituency_foodbanks[0].get("mp_party")
    mp_parl_id = constituency_foodbanks[0].get("mp_parl_id")

    template_vars = {
        "constituency_name":constituency_name,
        "constituency_slug":slugify(constituency_name),
        "mp":mp,
        "mp_party":mp_party,
        "mp_parl_id":mp_parl_id,
        "constituency_foodbanks":constituency_foodbanks,
        "constituency_locations":constituency_locations,
    }

    return render(request, "wfbn_constituency.html", template_vars)


@cache_page(60*30)
def public_wfbn_constituency_mp_photo(request, slug, size):

    parl_con = get_object_or_404(ParliamentaryConstituency, slug=slug)
    result = urlfetch.fetch("https://storage.googleapis.com/mp_photos/%s/%s.png" % (size, parl_con.mp_parl_id))

    return HttpResponse(result.content, content_type='image/png')


@csrf_exempt
def public_what_food_banks_need_updates(request, action):

    key = request.GET.get("key", None)
    email = request.POST.get("email", None)

    if action == "subscribe":

        try:
            validate_email(email)
        except forms.ValidationError:
            return HttpResponseForbidden()

        foodbank_slug = request.POST.get("foodbank")
        foodbank = get_object_or_404(Foodbank, slug=foodbank_slug)

        try:
            new_sub = FoodbankSubscriber(
                foodbank = foodbank,
                email = email,
            )
            new_sub.save()
            sub_key = new_sub.sub_key


            send_email(
                email,
                "Confirm your Give Food subscription",
                "Someone asked for updates on %s foodbank from Give Food. Please confirm this was you by clicking this link...\n\nhttps://www.givefood.org.uk/needs/updates/confirm/?key=%s" % (
                    foodbank.name,
                    sub_key,
                )
            )

            message = "Thanks, but we're not quite done yet. Check your email for a link to click to confirmation your subscription - you might have to check your spam folder though."

        except IntegrityError:

            message = "Sorry! That email address is already subscribed to that food bank."


    if action == "confirm":

        sub = get_object_or_404(FoodbankSubscriber, sub_key=key)
        sub.confirmed = True
        sub.save()

        message = "Great! Thank you for confirming your subscription."

    if action == "unsubscribe":

        sub = get_object_or_404(FoodbankSubscriber, unsub_key=key)
        sub.delete()

        message = "You have been unsubscribed."


    template_vars = {
        "message":message,
    }
    return render(request, "wfbn_updates.html", template_vars)



def public_wfbn_foodbank_edit(request, slug):

    foodbank = get_object_or_404(Foodbank, slug = slug)

    template_vars = {
        "foodbank":foodbank,
    }
    return render(request, "wfbn_foodbank_edit.html", template_vars)


@anonymous_csrf
def public_wfbn_foodbank_edit_form(request, slug, action, locslug = None):

    foodbank = get_object_or_404(Foodbank, slug = slug)
    location = None

    if action == "needs":
        heading = "Shopping List"
        if request.POST:
            form = NeedForm(request.POST)
            if form.is_valid():
                foodbank_change = form.save(commit=False)
                foodbank_change.foodbank = foodbank
                foodbank_change.input_method = "user"
                foodbank_change.save()
                return redirect("public_wfbn_foodbank_edit_thanks", slug = slug)
        else:
            form = NeedForm(instance=foodbank.latest_need())

    if action == "locations":
        heading = "Locations"

        if locslug:
            location = get_object_or_404(FoodbankLocation, foodbank = foodbank, slug = locslug)
            form = LocationLocationForm(instance=location)
        else:
            location = None
            form = FoodbankLocationForm(instance=foodbank)

        if request.POST:
            post_to_email(request.POST, {
                "foodbank":foodbank.name,
                "location":location,
            })
            return redirect("public_wfbn_foodbank_edit_thanks", slug = slug)

    if action == "contacts":
        heading = "Contact Information"
        form = ContactForm(instance=foodbank)

        if request.POST:
            post_to_email(request.POST, {
                "foodbank":foodbank.name,
            })
            return redirect("public_wfbn_foodbank_edit_thanks", slug = slug)

    if action == "closed":
        heading = "Closed"
        form = None

        if request.POST:
            post_to_email(request.POST, {
                "foodbank":foodbank.name,
            }, "CLOSED")
            return redirect("public_wfbn_foodbank_edit_thanks", slug = slug)

    template_vars = {
        "foodbank":foodbank,
        "action":action,
        "locslug":locslug,
        "location":location,
        "form":form,
        "heading":heading,
    }
    return render(request, "wfbn_foodbank_edit_form.html", template_vars)


def public_wfbn_foodbank_edit_thanks(request, slug):

    foodbank = get_object_or_404(Foodbank, slug = slug)
    template_vars = {
        "foodbank":foodbank,
    }
    return render(request, "wfbn_foodbank_edit_thanks.html", template_vars)