import requests, datetime

from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseRedirect, HttpResponse, HttpResponseForbidden, HttpResponseNotFound
from django.db import IntegrityError
from django.template.loader import render_to_string
from django.views.decorators.cache import cache_page, never_cache
from django.template.defaultfilters import slugify
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.core.validators import validate_email
from django import forms
from django.db.models import Sum

from session_csrf import anonymous_csrf
from requests.models import PreparedRequest

from givefood.models import Foodbank, FoodbankHit, FoodbankLocation, ParliamentaryConstituency, FoodbankChange, FoodbankSubscriber, FoodbankArticle
from givefood.func import geocode, find_locations, admin_regions_from_postcode, get_cred, send_email, post_to_email, get_all_constituencies, validate_turnstile
from givefood.const.cache_times import SECONDS_IN_DAY, SECONDS_IN_WEEK
from gfwfbn.forms import NeedForm, ContactForm, FoodbankLocationForm, LocationLocationForm


@cache_page(SECONDS_IN_DAY)
def index(request):

    # Handle old misspelt URL
    if request.GET.get("lattlong", None):
        return redirect("%s?lat_lng=%s" % (reverse("wfbn:index"), request.GET.get("lattlong")))

    address = request.GET.get("address", "")
    lat_lng = request.GET.get("lat_lng", "")
    where_from = request.GET.get("from","")
    
    location_results = []
    recently_updated = FoodbankChange.objects.filter(published = True).order_by("-created")[:10]
    most_viewed = FoodbankHit.objects.raw("SELECT 1 as id, (select name from givefood_foodbank where id = foodbank_id) as name, (select slug from givefood_foodbank where id = foodbank_id) as slug, SUM(hits) as sumhits FROM givefood_foodbankhit WHERE day >= CURRENT_DATE - 7 and day <= CURRENT_DATE GROUP BY foodbank_id ORDER BY sumhits DESC LIMIT 10")

    if address and not lat_lng:
        lat_lng = geocode(address)

    if lat_lng:
        location_results = find_locations(lat_lng, 10)

        for location in location_results:
            location_need = FoodbankChange.objects.filter(foodbank_name=location.get("foodbank_name"), published=True).latest("created")
            location["needs"] = location_need.change_text

    gmap_key = get_cred("gmap_key")

    template_vars = {
        "where_from":where_from,
        "address":address,
        "lat_lng":lat_lng,
        "gmap_key":gmap_key,
        "recently_updated":recently_updated,
        "most_viewed":most_viewed,
        "location_results":location_results,
    }
    return render(request, "wfbn/index.html", template_vars)


@cache_page(SECONDS_IN_WEEK)
def rss(request):

    needs = FoodbankChange.objects.filter(published = True).order_by("-created")[:10]
    news = FoodbankArticle.objects.all().order_by("-published_date")[:10]

    items = []
    for need in needs:
        items.append({
            "title":"%s items requested at %s" % (need.no_items(), need.foodbank.full_name()),
            "url":"https://www.givefood.org.uk/needs/at/%s/history/#need-%s" % (need.foodbank.slug, need.need_id),
            "date":need.created,
            "description":need.clean_change_text()
        })
    for newsitem in news:
        items.append({
            "title":newsitem.title,
            "url":newsitem.url,
            "date":newsitem.published_date,
        })

    items = sorted(items, key=lambda d: d['date'], reverse=True) 

    template_vars = {
        "items":items,
    }

    return render(request, "wfbn/rss.xml", template_vars, content_type='text/xml')


@cache_page(SECONDS_IN_WEEK)
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

    added_params = {"ref":"givefood.org.uk"}
    req = PreparedRequest()
    req.prepare_url(foodbank.url, added_params)
    response = redirect(req.url)
    response["X-Robots-Tag"] = "noindex"
    return response


@cache_page(SECONDS_IN_WEEK)
def foodbank(request, slug):

    foodbank = get_object_or_404(Foodbank, slug = slug)

    change_text = foodbank.latest_need().change_text

    if change_text == "Unknown" or change_text == "Nothing":
        template = "noneed"
    else:
        template = "withneed"

    template_vars = {
        "section":"foodbank",
        "foodbank":foodbank,
    }

    return render(request, "wfbn/foodbank/index_%s.html" % (template), template_vars)


@cache_page(SECONDS_IN_WEEK)
def foodbank_rss(request, slug):

    foodbank = get_object_or_404(Foodbank, slug = slug)

    needs = FoodbankChange.objects.filter(foodbank = foodbank, published = True).order_by("-created")[:10]
    news = FoodbankArticle.objects.filter(foodbank = foodbank).order_by("-published_date")[:10]

    items = []
    for need in needs:
        items.append({
            "title":"%s items requested at %s" % (need.no_items(), foodbank.full_name()),
            "url":"https://www.givefood.org.uk/needs/at/%s/history/#need-%s" % (foodbank.slug, need.need_id),
            "date":need.created,
            "description":need.clean_change_text()
        })
    for newsitem in news:
        items.append({
            "title":newsitem.title,
            "url":newsitem.url,
            "date":newsitem.published_date,
        })

    items = sorted(items, key=lambda d: d['date'], reverse=True) 

    template_vars = {
        "foodbank":foodbank,
        "items":items,
    }

    return render(request, "wfbn/rss.xml", template_vars, content_type='text/xml')


@cache_page(SECONDS_IN_WEEK)
def foodbank_map(request, slug):

    foodbank = get_object_or_404(Foodbank, slug = slug)
    gmap_static_key = get_cred("gmap_static_key")

    markers = "%s|" % foodbank.latt_long
    for location in foodbank.locations():
        markers = "%s%s|" % (markers, location.latt_long)

    if foodbank.name == "Salvation Army":
        markers = "&zoom=15"

    url = "https://maps.googleapis.com/maps/api/staticmap?center=%s&size=600x400&maptype=roadmap&format=png&visual_refresh=true&key=%s&markers=%s" % (foodbank.latt_long, gmap_static_key, markers)

    request = requests.get(url)
    return HttpResponse(request.content, content_type='image/png')


@cache_page(SECONDS_IN_WEEK)
def foodbank_locations(request,slug):

    foodbank = get_object_or_404(Foodbank, slug = slug)
    if foodbank.no_locations == 0:
        return HttpResponseNotFound()

    template_vars = {
        "section":"locations",
        "foodbank":foodbank,
    }

    return render(request, "wfbn/foodbank/locations.html", template_vars)


@cache_page(SECONDS_IN_DAY)
def foodbank_news(request,slug):

    foodbank = get_object_or_404(Foodbank, slug = slug)
    if not foodbank.rss_url:
        return HttpResponseNotFound()

    template_vars = {
        "section":"news",
        "foodbank":foodbank,
    }

    return render(request, "wfbn/foodbank/news.html", template_vars)


@cache_page(SECONDS_IN_WEEK)
def foodbank_history(request, slug):

    foodbank = get_object_or_404(Foodbank, slug = slug)
        
    needs = FoodbankChange.objects.filter(foodbank = foodbank, published = True).order_by("-created")[:10]

    template_vars = {
        "section":"history",
        "foodbank":foodbank,
        "needs":needs,
    }

    return render(request, "wfbn/foodbank/history.html", template_vars)


@cache_page(SECONDS_IN_WEEK)
def foodbank_socialmedia(request, slug):

    foodbank = get_object_or_404(Foodbank, slug = slug)
    # TODO: check if fb has social media

    template_vars = {
        "section":"socialmedia",
        "foodbank":foodbank,
    }

    return render(request, "wfbn/foodbank/socialmedia.html", template_vars)


@cache_page(SECONDS_IN_WEEK)
def foodbank_nearby(request, slug):

    foodbank = get_object_or_404(Foodbank, slug = slug)
    nearby_locations = find_locations(foodbank.latt_long, 20, True)

    template_vars = {
        "section":"nearby",
        "foodbank":foodbank,
        "nearby":nearby_locations,
    }

    return render(request, "wfbn/foodbank/nearby.html", template_vars)


@cache_page(SECONDS_IN_WEEK)
def foodbank_subscribe(request, slug):

    foodbank = get_object_or_404(Foodbank, slug = slug)
    email = request.GET.get("email", None)
    turnstilefail = request.GET.get("email", None)

    template_vars = {
        "section":"subscribe",
        "foodbank":foodbank,
        "email":email,
        "turnstilefail":turnstilefail,
    }

    return render(request, "wfbn/foodbank/subscribe.html", template_vars)


@cache_page(SECONDS_IN_WEEK)
def foodbank_subscribe_sample(request, slug):

    foodbank = get_object_or_404(Foodbank, slug = slug)

    template_vars = {
        "need":foodbank.latest_need(),
        "is_sample":True,
    }

    return render(request, "wfbn/emails/notification.html", template_vars)


@cache_page(SECONDS_IN_WEEK)
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


@cache_page(SECONDS_IN_WEEK)
def foodbank_location_map(request, slug, locslug):

    foodbank = get_object_or_404(Foodbank, slug = slug)
    location = get_object_or_404(FoodbankLocation, slug = locslug, foodbank = foodbank)
    gmap_static_key = get_cred("gmap_static_key")

    url = "https://maps.googleapis.com/maps/api/staticmap?center=%s&zoom=15&size=600x400&maptype=roadmap&format=png&visual_refresh=true&key=%s" % (location.latt_long, gmap_static_key)
    request = requests.get(url)

    return HttpResponse(request.content, content_type='image/png')


@cache_page(SECONDS_IN_WEEK)
def constituencies(request):

    postcode = request.GET.get("postcode", None)
    if postcode:
        admin_regions = admin_regions_from_postcode(postcode)
        parl_con = admin_regions.get("parliamentary_constituency", None)
        if parl_con:
            return HttpResponseRedirect(reverse("wfbn:constituency", kwargs={"slug":slugify(parl_con)}))

    constituencies = get_all_constituencies()

    template_vars = {
        "constituencies":constituencies,
        "postcode":postcode,
    }

    return render(request, "wfbn/constituency/index.html", template_vars)


@cache_page(SECONDS_IN_WEEK)
def constituency(request, slug):

    constituency = get_object_or_404(ParliamentaryConstituency, slug = slug)

    template_vars = {
        "constituency":constituency,
    }

    return render(request, "wfbn/constituency/constituency.html", template_vars)


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
        
        turnstile_is_valid = validate_turnstile(request.POST.get("cf-turnstile-response"))

        if not turnstile_is_valid:
            return HttpResponseRedirect("%s?turnstilefail=true&email=%s" % (reverse("wfbn:foodbank_subscribe", kwargs={"slug":foodbank.slug}), email))

        # TODO - check subscriber dupe here, rather than inside the try

        try:
            new_sub = FoodbankSubscriber(
                foodbank = foodbank,
                email = email,
            )
            new_sub.save()

            template_vars = {
                "foodbank":foodbank,
                "sub_key":new_sub.sub_key,
            }

            text_body = render_to_string("wfbn/emails/confirm.txt", template_vars)
            html_body = render_to_string("wfbn/emails/confirm.html", template_vars)


            send_email(
                to = email,
                subject = "Confirm your Give Food subscription",
                body = text_body,
                html_body = html_body,
            )

            message = "Thanks, but we're not quite done yet.\n\nWe've sent an email to %s with a link to click to confirm your subscription. You might have to look in your spam folder though." % (email)

        except IntegrityError:

            message = "Sorry! That email address is already subscribed to that food bank."


    if action == "confirm":

        sub = get_object_or_404(FoodbankSubscriber, sub_key=key)

        if not sub.confirmed:
            sub.confirmed = True
            sub.save()

            template_vars = {
                "foodbank":sub.foodbank,
            }

            text_body = render_to_string("wfbn/emails/confirmed.txt", template_vars)
            html_body = render_to_string("wfbn/emails/confirmed.html", template_vars)

            send_email(
                to = sub.email,
                subject = "Thank you for confirming your subscription to %s Food Bank" % (foodbank.name),
                body = text_body,
                html_body = html_body,
            )

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


@never_cache
def foodbank_hit(request, slug):
    
    foodbank = get_object_or_404(Foodbank, slug = slug)
    day = datetime.datetime.today()

    try:
        hit = FoodbankHit.objects.get(foodbank = foodbank, day = day)
        hit.hits += 1
        hit.save()
    except FoodbankHit.DoesNotExist:
        hit = FoodbankHit(foodbank = foodbank, day = day, hits = 1)
        hit.save()
    
    return HttpResponse("", content_type="text/javascript")


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
            if locslug == "new":
                form = FoodbankLocationForm()
            else:
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