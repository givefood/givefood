from django.shortcuts import render, get_object_or_404
from django.template.defaultfilters import slugify
from django.template.loader import render_to_string
from django.http import HttpResponseRedirect, HttpResponseNotFound
from django.urls import reverse

from givefood.func import admin_regions_from_postcode, send_email
from givefood.models import ConstituencySubscriber, ParliamentaryConstituency
from gfwrite.forms import ConstituentDetailsForm, EmailForm

def index(request):

    postcode = request.GET.get("postcode", None)
    if postcode:
        admin_regions = admin_regions_from_postcode(postcode)
        parl_con = admin_regions.get("parliamentary_constituency", None)
        if parl_con:
            parl_con_url = "%s?postcode=%s" % (
                reverse("write:constituency", kwargs={"slug":slugify(parl_con)}),
                postcode
            )
            return HttpResponseRedirect(parl_con_url)

    template_vars = {}
    return render(request, "write/index.html", template_vars)


def constituency(request, slug):

    constituency = get_object_or_404(ParliamentaryConstituency, slug = slug)
    postcode = request.GET.get("postcode", None)

    template_vars = {
        "constituency":constituency,
        "postcode":postcode,
        "form":ConstituentDetailsForm,
    }

    return render(request, "write/constituency.html", template_vars)


def email(request, slug):

    constituency = get_object_or_404(ParliamentaryConstituency, slug = slug)

    if request.POST:
        form = ConstituentDetailsForm(request.POST)

        if form.is_valid():
            name = request.POST.get("name")
            email = request.POST.get("email")

            if request.POST.get("subscribe"):
                constituency_subscriber = ConstituencySubscriber(
                    name = name,
                    email = email,
                    parliamentary_constituency = constituency,
                )
                constituency_subscriber.save()

            to_field = "%s <%s>" % (constituency.mp_display_name, constituency.email_parl)
            from_field = "%s <%s>" % (name, email)
            subject = "Food Banks in %s" % (constituency.name)

            foodbanks = constituency.foodbank_names()
            body = render_to_string("write/email.txt", {
                "address":request.POST.get("address"),
                "name":request.POST.get("name"),
                "constituency":constituency,
                "foodbanks":foodbanks
            })

            form = EmailForm(initial={
                "to_field":to_field,
                "from_field":from_field,
                "from_name":name,
                "from_email":email,
                "subject":subject,
                "body":body,
            })

            template_vars = {
                "constituency":constituency,
                "form":form,
            }
            return render(request, "write/email.html", template_vars)
        else:
            template_vars = {
                "constituency":constituency,
                "form":ConstituentDetailsForm,
            }
            return render(request, "write/constituency.html", template_vars)

    else:
        return HttpResponseNotFound()


def send(request, slug):

    constituency = get_object_or_404(ParliamentaryConstituency, slug = slug)

    if request.POST:
        form = EmailForm(request.POST)
        if form.is_valid():
            send_email(
                to = constituency.email_parl,
                subject = form.data["subject"],
                body = form.data["body"],
                cc = form.data["from_email"],
                cc_name = form.data["from_name"],
                reply_to = form.data["from_email"],
                reply_to_name = form.data["from_name"],
            )
            done_url = "%s?email=%s" % (
                reverse("write:done", kwargs={"slug":constituency.slug}),
                form.data["from_email"],
            )
            return HttpResponseRedirect(done_url)
        else:
            template_vars = {
                "constituency":constituency,
                "form":form,
            }
            return render(request, "write/email.html", template_vars)


def done(request, slug):

    constituency = get_object_or_404(ParliamentaryConstituency, slug = slug)
    email = request.GET.get("email")
    template_vars = {
        "constituency":constituency,
        "email":email,
    }
    return render(request, "write/done.html", template_vars)