import json, requests, datetime, logging

from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseRedirect, HttpResponse, HttpResponseForbidden, HttpResponseNotFound, JsonResponse, HttpResponseBadRequest
from django.db import IntegrityError
from django.template.loader import render_to_string
from django.views.decorators.cache import cache_page, never_cache
from django.template.defaultfilters import slugify
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.core.validators import validate_email
from django import forms
from django.utils.translation import gettext

from givefood.const.general import SITE_DOMAIN
from givefood.forms import FoodbankDonationPointForm
from session_csrf import anonymous_csrf

from givefood.models import Foodbank, FoodbankDonationPoint, FoodbankHit, FoodbankLocation, ParliamentaryConstituency, FoodbankChange, FoodbankSubscriber, FoodbankArticle
from givefood.func import geocode, find_locations, admin_regions_from_postcode, get_cred, is_uk, photo_from_place_id, send_email, post_to_email, get_all_constituencies, validate_turnstile
from givefood.const.cache_times import SECONDS_IN_DAY, SECONDS_IN_WEEK
from gfwfbn.forms import NeedForm, ContactForm, FoodbankLocationForm, LocationLocationForm


@cache_page(SECONDS_IN_DAY)
def index(request):
    """
    The What Food Banks Need index page
    """ 

    # Handle old misspelt URL
    if request.GET.get("lattlong", None):
        return redirect("%s?lat_lng=%s" % (reverse("wfbn:index"), request.GET.get("lattlong")), permanent=True)

    # All the vars we'll need
    address = request.GET.get("address", "")
    lat_lng = request.GET.get("lat_lng", "")
    lat = None
    lng = None
    lat_lng_is_uk = True
    location_results = []

    # Recently updated food banks
    recently_updated = FoodbankChange.objects.filter(published = True).order_by("-created")[:10]

    # Most viewed food banks
    most_viewed = FoodbankHit.objects.raw("SELECT 1 as id, (select name from givefood_foodbank where id = foodbank_id) as name, (select slug from givefood_foodbank where id = foodbank_id) as slug, SUM(hits) as sumhits FROM givefood_foodbankhit WHERE day >= CURRENT_DATE - 7 and day <= CURRENT_DATE GROUP BY foodbank_id ORDER BY sumhits DESC LIMIT 10")

    # Geocode address if no lat_lng
    if address and not lat_lng:
        lat_lng = geocode(address)

    if lat_lng:

        # Validate lat_lng
        try:
            lat = lat_lng.split(",")[0]
            lng = lat_lng.split(",")[1]
        except IndexError:
            return HttpResponseBadRequest()
        
        # Check if lat_lng is in UK
        lat_lng_is_uk = is_uk(lat_lng)

        if lat_lng_is_uk:

            # Do the search
            location_results = find_locations(lat_lng, 10)

            # Add needs to location results
            for location in location_results:
                try:
                    location_need = FoodbankChange.objects.filter(foodbank_name=location.get("foodbank_name"), published=True).latest("created")
                    location["needs"] = location_need.change_text
                except FoodbankChange.DoesNotExist:
                    logging.warn("No need found for %s" % location.get("foodbank_name"))
                    location["needs"] = "Unknown"            
                location["url"] = Foodbank.objects.get(name=location.get("foodbank_name")).url_with_ref()

    # Need the Google Maps API key too
    gmap_key = get_cred("gmap_key")

    template_vars = {
        "address":address,
        "lat":lat,
        "lng":lng,
        "gmap_key":gmap_key,
        "recently_updated":recently_updated,
        "most_viewed":most_viewed,
        "location_results":location_results,
        "is_uk":lat_lng_is_uk,
    }
    return render(request, "wfbn/index.html", template_vars)


@cache_page(SECONDS_IN_WEEK)
def rss(request):
    """
    Site-wide RSS feed
    """ 

    # Get needs
    needs = FoodbankChange.objects.filter(published = True).exclude(change_text = "Nothing").exclude(change_text = "Facebook").exclude(change_text = "Unknown").order_by("-created")[:10]
    # Get news
    news = FoodbankArticle.objects.all().order_by("-published_date")[:10]

    # Put them all together
    items = []
    for need in needs:
        items.append({
            "title":"%s items requested at %s" % (need.no_items(), need.foodbank.full_name()),
            "url":"https://www.givefood.org.uk/needs/at/%s/history/#need-%s" % (need.foodbank.slug, need.need_id),
            "date":need.created,
            "description":need.change_text,
        })
    for newsitem in news:
        items.append({
            "title":newsitem.title,
            "url":newsitem.url,
            "date":newsitem.published_date,
        })

    # Sort all the items by date
    items = sorted(items, key=lambda d: d['date'], reverse=True) 

    template_vars = {
        "items":items,
    }

    return render(request, "wfbn/rss.xml", template_vars, content_type='text/xml')


def get_location(request):
    """
    Handle non-javascript location requests
    """

    lat_lng = request.META.get("HTTP_X_APPENGINE_CITYLATLONG")
    url = reverse("wfbn:index")
    redirect_url = "%s?lat_lng=%s" % (url, lat_lng)
    return redirect(redirect_url)


@cache_page(SECONDS_IN_WEEK)
def geojson(request, slug = None, parlcon_slug = None):
    """
    GeoJSON for everything, a food bank or a parliamentary constituency
    """

    # All items
    all_items = not slug and not parlcon_slug

    # Handle bad fb slug
    if slug:
        foodbank = get_object_or_404(Foodbank, slug = slug)

    if slug:
        foodbanks = Foodbank.objects.filter(slug = slug)
        locations = FoodbankLocation.objects.filter(foodbank__slug = slug)
        donationpoints = FoodbankDonationPoint.objects.filter(foodbank__slug = slug)
    elif parlcon_slug:
        foodbanks = Foodbank.objects.filter(parliamentary_constituency_slug = parlcon_slug, is_closed=False)
        locations = FoodbankLocation.objects.filter(parliamentary_constituency_slug = parlcon_slug, is_closed=False)
        donationpoints = FoodbankDonationPoint.objects.filter(parliamentary_constituency_slug = parlcon_slug, is_closed=False)
    else:
        foodbanks = Foodbank.objects.filter(is_closed=False)
        locations = FoodbankLocation.objects.filter(is_closed=False)
        donationpoints = FoodbankDonationPoint.objects.filter(is_closed=False)

    features = []

    # Parlcon outline
    if parlcon_slug:
        parlcon = get_object_or_404(ParliamentaryConstituency, slug = parlcon_slug)
        boundary = parlcon.boundary_geojson_dict()
        boundary["properties"]["type"] = "b"
        features.append(boundary)

    for foodbank in foodbanks:
        features.append({
            "type":"Feature",
            "geometry":{
                "type":"Point",
                "coordinates":[foodbank.long(), foodbank.latt()],
            },
            "properties":{
                "type":"f",
                "name":foodbank.full_name(),
                "address":foodbank.full_address(),
                "url":"/needs/at/%s/" % foodbank.slug,
            }
        })
        if foodbank.delivery_address:
            features.append({
                "type":"Feature",
                "geometry":{
                    "type":"Point",
                    "coordinates":[foodbank.delivery_long(), foodbank.delivery_latt()],
                },
                "properties":{
                    "type":"f",
                    "name":"%s Delivery Address" % (foodbank.full_name()),
                    "address":foodbank.delivery_address,
                    "url":"/needs/at/%s/" % foodbank.slug,
                }
            })
    
    for location in locations:
        features.append({
            "type":"Feature",
            "geometry":{
                "type":"Point",
                "coordinates":[location.long(), location.latt()],
            },
            "properties":{
                "type":"l",
                "name":location.name,
                "foodbank":location.foodbank_name,
                "address":location.full_address(),
                "url":"/needs/at/%s/%s/" % (location.foodbank_slug, location.slug),
            }
        })

    for donationpoint in donationpoints:
        features.append({
            "type":"Feature",
            "geometry":{
                "type":"Point",
                "coordinates":[donationpoint.long(), donationpoint.latt()],
            },
            "properties":{
                "type":"d",
                "name":donationpoint.name,
                "foodbank":donationpoint.foodbank_name,
                "address":donationpoint.full_address(),
                "url":"/needs/at/%s/donationpoint/%s/" % (donationpoint.foodbank_slug, donationpoint.slug),
            }
        })

    # Remove address if all items (for download size)
    if all_items:
        for feature in features:
            feature["properties"].pop("address", None)

    response_dict = {
            "type": "FeatureCollection",
            "features": features
    }

    return JsonResponse(response_dict)


@cache_page(SECONDS_IN_DAY)
def manifest(request):
    """
    Web app manifest
    """

    scope = reverse("wfbn:index")
    start_url = "%s%s" % (SITE_DOMAIN, reverse("wfbn:index"))
    lang = request.LANGUAGE_CODE

    manifest_content = {
        "name" : "Give Food",
        "short_name" : "Give Food",
        "description" : gettext("Use Give Food's tool to find what food banks near you are requesting to have donated"),
        "start_url" : start_url,
        "scope" : scope,
        "display" : "minimal-ui",
        "lang" : lang,
        "icons": [
            {
                "src": "/static/img/favicon.svg",
                "type": "image/svg",
                "sizes": "48x48 72x72 96x96 128x128 256x256 512x512",
                "type": "image/svg+xml",
                "purpose": "any"
            }
        ],
        "screenshots": [
            {
                "src": "/static/img/manifestscreens/index.png",
                "type": "image/png",
                "sizes": "1402x2356"
            },
            {
                "src": "/static/img/manifestscreens/search.png",
                "type": "image/png",
                "sizes": "1402x2356"
            },
            {
                "src": "/static/img/manifestscreens/foodbank.png",
                "type": "image/png",
                "sizes": "1402x2356"
            }
        ]
    }

    return HttpResponse(json.dumps(manifest_content), content_type="application/json")


@cache_page(SECONDS_IN_WEEK)
def foodbank(request, slug):
    """
    Food bank index
    """

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
    """
    Food bank RSS feed
    """

    foodbank = get_object_or_404(Foodbank, slug = slug)

    needs = FoodbankChange.objects.filter(foodbank = foodbank, published = True).exclude(change_text = "Nothing").exclude(change_text = "Facebook").exclude(change_text = "Unknown").order_by("-created")[:10]
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
    """
    Food bank map PNG
    """

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
    """
    Food bank locations index
    """

    foodbank = get_object_or_404(Foodbank, slug = slug)
    if foodbank.no_locations == 0:
        return HttpResponseNotFound()

    template_vars = {
        "section":"locations",
        "foodbank":foodbank,
    }

    return render(request, "wfbn/foodbank/locations.html", template_vars)


@cache_page(SECONDS_IN_WEEK)
def foodbank_donationpoints(request,slug):
    """
    Food bank donation points index
    """

    foodbank = get_object_or_404(Foodbank, slug = slug)
    if foodbank.no_donation_points == 0:
        return HttpResponseNotFound()

    template_vars = {
        "section":"donationpoints",
        "foodbank":foodbank,
    }

    return render(request, "wfbn/foodbank/donationpoints.html", template_vars)

@cache_page(SECONDS_IN_DAY)
def foodbank_news(request,slug):
    """
    Food bank news
    """

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
    """
    Food bank need history
    """

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
    """
    Food bank social media links
    """

    foodbank = get_object_or_404(Foodbank, slug = slug)
    # TODO: check if fb has social media

    template_vars = {
        "section":"socialmedia",
        "foodbank":foodbank,
    }

    return render(request, "wfbn/foodbank/socialmedia.html", template_vars)


@cache_page(SECONDS_IN_WEEK)
def foodbank_nearby(request, slug):
    """
    Food bank nearby list
    """

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
    """
    Food bank subscribe page
    """

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
    """
    Food bank subscribe sample email
    Used in an iframe in the subscribe page
    """

    foodbank = get_object_or_404(Foodbank, slug = slug)

    template_vars = {
        "need":foodbank.latest_need(),
        "is_sample":True,
    }

    return render(request, "wfbn/emails/notification.html", template_vars)


@cache_page(SECONDS_IN_WEEK)
def foodbank_location(request, slug, locslug):
    """
    Food bank individual location
    """

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
    """
    Food bank location map PNG
    """

    foodbank = get_object_or_404(Foodbank, slug = slug)
    location = get_object_or_404(FoodbankLocation, slug = locslug, foodbank = foodbank)
    gmap_static_key = get_cred("gmap_static_key")

    url = "https://maps.googleapis.com/maps/api/staticmap?center=%s&zoom=15&size=600x400&maptype=roadmap&format=png&visual_refresh=true&key=%s" % (location.latt_long, gmap_static_key)
    request = requests.get(url)

    return HttpResponse(request.content, content_type='image/png')


@cache_page(SECONDS_IN_WEEK)
def foodbank_location_photo(request, slug, locslug):
    """
    Food bank location photo JPEG
    """

    size = request.GET.get("size", 1080)
    foodbank = get_object_or_404(Foodbank, slug = slug)
    location = get_object_or_404(FoodbankLocation, slug = locslug, foodbank = foodbank)

    if not location.place_has_photo:
        return HttpResponseNotFound()
    
    photo = photo_from_place_id(location.place_id, size)
    
    return HttpResponse(photo, content_type='image/jpeg')


@cache_page(SECONDS_IN_WEEK)
def foodbank_donationpoint(request, slug, dpslug):
    """
    Food bank donation point
    """

    foodbank = get_object_or_404(Foodbank, slug = slug)
    donationpoint = get_object_or_404(FoodbankDonationPoint, slug = dpslug, foodbank = foodbank)

    change_text = foodbank.latest_need().change_text
    if change_text == "Unknown" or change_text == "Nothing" or change_text == "Facebook":
        has_need = False
    else:
        has_need = True

    template_vars = {
        "section":"donationpoints",
        "foodbank":foodbank,
        "has_need":has_need,
        "donationpoint":donationpoint,
    }

    return render(request, "wfbn/foodbank/donationpoint.html", template_vars)


@cache_page(SECONDS_IN_WEEK)
def foodbank_donationpoint_photo(request, slug, dpslug):
    """
    Food bank donation point photo JPEG
    """

    size = request.GET.get("size", 1080)
    foodbank = get_object_or_404(Foodbank, slug = slug)
    donationpoint = get_object_or_404(FoodbankDonationPoint, slug = dpslug, foodbank = foodbank)

    if not donationpoint.place_has_photo:
        return HttpResponseNotFound()
    
    photo = photo_from_place_id(donationpoint.place_id, size)
    
    return HttpResponse(photo, content_type='image/jpeg')


@cache_page(SECONDS_IN_WEEK)
def constituencies(request):
    """
    Food bank constituencies index
    """

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
    """
    Food bank constituency
    """

    constituency = get_object_or_404(ParliamentaryConstituency, slug = slug)

    template_vars = {
        "constituency":constituency,
    }

    return render(request, "wfbn/constituency/constituency.html", template_vars)


@csrf_exempt
def updates(request, slug, action):
    """
    Food bank updates pages
    Subscribe, confirm, unsubscribe acions
    """

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

        if not key:
            return HttpResponseForbidden()

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
    """
    Food bank hit counter
    """
    
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
    """
    Food bank edit form
    """

    foodbank = get_object_or_404(Foodbank, slug = slug)
    location = None
    donationpoint = None

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
    
    if action == "donationpoints":
        heading = "Donation Points"

        if locslug:
            if locslug == "new":
                form = FoodbankDonationPointForm()
            else:
                donationpoint = get_object_or_404(FoodbankDonationPoint, foodbank = foodbank, slug = locslug)
                form = FoodbankDonationPointForm(instance=donationpoint)
        else:
            donationpoint = None
            form = FoodbankDonationPointForm(instance=donationpoint)

        if request.POST:
            post_to_email(request.POST, {
                "foodbank":foodbank.name,
                "donationpoint":donationpoint,
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
        "donationpoint":donationpoint,
        "form":form,
        "heading":heading,
    }
    return render(request, "wfbn/foodbank/edit/form.html", template_vars)


def foodbank_edit_thanks(request, slug):
    """
    Food bank edit thanks page
    """

    foodbank = get_object_or_404(Foodbank, slug = slug)
    template_vars = {
        "section":"edit",
        "foodbank":foodbank,
    }
    return render(request, "wfbn/foodbank/edit/thanks.html", template_vars)