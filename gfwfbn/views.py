import logging

from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseRedirect, HttpResponse, HttpResponseForbidden, Http404, HttpResponseNotFound
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
from givefood.func import get_all_foodbanks, get_all_locations, find_foodbanks, geocode, find_locations, admin_regions_from_postcode, get_cred, send_email, post_to_email
from gfwfbn.forms import NeedForm, ContactForm, FoodbankLocationForm, LocationLocationForm


@cache_page(60*10)
def index(request):

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
    return render(request, "wfbn/index.html", template_vars)


@cache_page(60*10)
def trussell_trust_index(request):

    gmap_key = get_cred("gmap_key")

    template_vars = {
        "gmap_key":gmap_key,
        "headless":True,
    }
    return render(request, "wfbn/trussell_trust.html", template_vars)


def get_location(request):

    lat_lng = request.META.get("HTTP_X_APPENGINE_CITYLATLONG")
    redirect_url = "/needs/?lat_lng=%s" % (lat_lng)
    return redirect(redirect_url)


def click(request, slug):

    foodbank = get_object_or_404(Foodbank, slug = slug)
    utm_querystring = "?utm_source=givefood_org_uk&utm_medium=search&utm_campaign=needs"
    redirect_url = "%s%s" % (
        foodbank.shopping_list_url,
        utm_querystring,
    )
    return redirect(redirect_url)


@cache_page(60*10)
def foodbank(request, slug):

    foodbank = get_object_or_404(Foodbank, slug = slug)
    nearby_locations = find_locations(foodbank.latt_long, 20, True)

    change_text = foodbank.latest_need().change_text

    if change_text == "Unknown" or change_text == "Nothing":
        template = "noneed"
    else:
        template = "withneed"

    template_vars = {
        "section":"foodbank",
        "foodbank":foodbank,
        "nearby_locations":nearby_locations,
    }

    return render(request, "wfbn/foodbank/index_%s.html" % (template), template_vars)


@cache_page(60*60)
def foodbank_map(request, slug):

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


@cache_page(60*30)
def foodbank_locations(request,slug):

    foodbank = get_object_or_404(Foodbank, slug = slug)
    if foodbank.no_locations == 0:
        return HttpResponseNotFound()

    template_vars = {
        "section":"locations",
        "foodbank":foodbank,
    }

    return render(request, "wfbn/foodbank/locations.html", template_vars)


@cache_page(60*30)
def foodbank_news(request,slug):

    foodbank = get_object_or_404(Foodbank, slug = slug)
    # TODO: check if fb has news

    template_vars = {
        "section":"news",
        "foodbank":foodbank,
    }

    return render(request, "wfbn/foodbank/news.html", template_vars)


@cache_page(60*10)
def foodbank_history(request, slug):

    foodbank = get_object_or_404(Foodbank, slug = slug)
    needs = FoodbankChange.objects.filter(foodbank = foodbank, published = True).order_by("-created")[:25]

    template_vars = {
        "section":"history",
        "foodbank":foodbank,
        "needs":needs,
    }

    return render(request, "wfbn/foodbank/history.html", template_vars)


@cache_page(60*30)
def foodbank_politics(request, slug):

    foodbank = get_object_or_404(Foodbank, slug = slug)

    template_vars = {
        "section":"politics",
        "foodbank":foodbank,
    }

    return render(request, "wfbn/foodbank/politics.html", template_vars)


@cache_page(60*30)
def foodbank_socialmedia(request, slug):

    foodbank = get_object_or_404(Foodbank, slug = slug)
    # TODO: check if fb has social media

    template_vars = {
        "section":"socialmedia",
        "foodbank":foodbank,
    }

    return render(request, "wfbn/foodbank/socialmedia.html", template_vars)


@cache_page(60*30)
def foodbank_nearby(request, slug):

    foodbank = get_object_or_404(Foodbank, slug = slug)
    nearby_locations = find_locations(foodbank.latt_long, 20, True)

    template_vars = {
        "section":"nearby",
        "foodbank":foodbank,
        "nearby":nearby_locations,
    }

    return render(request, "wfbn/foodbank/nearby.html", template_vars)


@cache_page(60*10)
def foodbank_location(request, slug, locslug):

    foodbank = get_object_or_404(Foodbank, slug = slug)
    location = get_object_or_404(FoodbankLocation, slug = locslug, foodbank = foodbank)

    change_text = foodbank.latest_need().change_text
    if change_text == "Unknown" or change_text == "Nothing":
        template = "noneed"
    else:
        template = "withneed"

    template_vars = {
        "section":"locations",
        "foodbank":foodbank,
        "location":location,
    }

    return render(request, "wfbn/foodbank/location_%s.html" % (template), template_vars)


@cache_page(60*30)
def foodbank_location_map(request, slug, locslug):

    foodbank = get_object_or_404(Foodbank, slug = slug)
    location = get_object_or_404(FoodbankLocation, slug = locslug, foodbank = foodbank)
    gmap_static_key = get_cred("gmap_static_key")

    result = urlfetch.fetch("https://maps.googleapis.com/maps/api/staticmap?center=%s&zoom=15&size=300x300&maptype=roadmap&format=png&visual_refresh=true&key=%s" % (location.latt_long, gmap_static_key))

    return HttpResponse(result.content, content_type='image/png')


@cache_page(60*10)
def constituencies(request):

    postcode = request.GET.get("postcode", None)
    if postcode:
        admin_regions = admin_regions_from_postcode(postcode)
        parl_con = admin_regions.get("parliamentary_constituency", None)
        if parl_con:
            return HttpResponseRedirect(reverse("wfbn:constituency", kwargs={"slug":slugify(parl_con)}))

    constituencies = ParliamentaryConstituency.objects.all().order_by("name")

    template_vars = {
        "constituencies":constituencies,
    }

    return render(request, "wfbn/constituency/index.html", template_vars)


@cache_page(60*10)
def constituency(request, slug):

    constituency = get_object_or_404(ParliamentaryConstituency, slug = slug)

    template_vars = {
        "constituency":constituency,
    }

    return render(request, "wfbn/constituency/constituency.html", template_vars)


@cache_page(60*60)
def constituency_mp_photo(request, slug, size):

    parl_con = get_object_or_404(ParliamentaryConstituency, slug=slug)
    result = urlfetch.fetch("https://storage.googleapis.com/mp_photos/%s/%s.png" % (size, parl_con.mp_parl_id))

    return HttpResponse(result.content, content_type='image/png')


@csrf_exempt
def updates(request, slug, action):

    key = request.GET.get("key", None)
    email = request.POST.get("email", None)
    foodbank = get_object_or_404(Foodbank, slug=slug)

    if action == "subscribe":

        try:
            validate_email(email)
        except forms.ValidationError:
            return HttpResponseForbidden()

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
                "Someone asked for updates on %s foodbank from Give Food. Please confirm this was you by clicking this link...\n\nhttps://www.givefood.org.uk/needs/at/%s/updates/confirm/?key=%s" % (
                    foodbank.name,
                    foodbank.slug,
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
        "section":"details",
        "foodbank":foodbank,
        "message":message,
    }
    return render(request, "wfbn/foodbank/updates.html", template_vars)



def foodbank_edit(request, slug):

    foodbank = get_object_or_404(Foodbank, slug = slug)

    template_vars = {
        "section":"edit",
        "foodbank":foodbank,
    }
    return render(request, "wfbn/foodbank/edit/index.html", template_vars)


@anonymous_csrf
def foodbank_edit_form(request, slug, action, locslug = None):

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
                return redirect("wfbn:foodbank_edit_thanks", slug = slug)
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
            return redirect("wfbn:foodbank_edit_thanks", slug = slug)

    if action == "contacts":
        heading = "Contact Information"
        form = ContactForm(instance=foodbank)

        if request.POST:
            post_to_email(request.POST, {
                "foodbank":foodbank.name,
            })
            return redirect("wfbn:foodbank_edit_thanks", slug = slug)

    if action == "closed":
        heading = "Closed"
        form = None

        if request.POST:
            post_to_email(request.POST, {
                "foodbank":foodbank.name,
            }, "CLOSED")
            return redirect("wfbn:foodbank_edit_thanks", slug = slug)

    template_vars = {
        "section":"edit",
        "foodbank":foodbank,
        "action":action,
        "locslug":locslug,
        "location":location,
        "form":form,
        "heading":heading,
    }
    return render(request, "wfbn/foodbank/edit/form.html", template_vars)


def foodbank_edit_thanks(request, slug):

    foodbank = get_object_or_404(Foodbank, slug = slug)
    template_vars = {
        "section":"edit",
        "foodbank":foodbank,
    }
    return render(request, "wfbn/foodbank/edit/thanks.html", template_vars)