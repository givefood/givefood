import time

from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.urls import resolve, reverse

from givefood.func import get_cred


# Inject the render time into the response content
def RenderTime(get_response):
    def middleware(request):
        t1 = time.time()
        response = get_response(request)
        t2 = time.time()
        duration = t2 - t1
        duration = round(duration * 1000, 3)
        response.content = response.content.replace(
            b"PUTTHERENDERTIMEHERE", bytes(str(duration), "utf-8"), 1
        )
        return response
    return middleware


# Check for a valid offline key in the URL for offline apps
class OfflineKeyCheck:

    key_check_apps = ["gfoffline"]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        if resolve(request.path).app_name in self.key_check_apps:

            key = request.GET.get("key", None)
            if key != get_cred("offline_key"):
                return HttpResponseForbidden("Invalid key")

        return self.get_response(request)


# Check if the user is logged in for specific apps
class LoginRequiredAccess:

    login_apps = ["gfadmin"]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        if resolve(request.path).app_name in self.login_apps:

            try:
                request.session.get("user_data").get("email")
                email_verified = request.session.get(
                    "user_data"
                ).get("email_verified")
                hosted_domain = request.session.get(
                    "user_data"
                ).get("hd")
            except AttributeError:
                return redirect("auth:sign_in")

            if not email_verified or hosted_domain != "givefood.org.uk":
                return redirect("auth:sign_in")

        return self.get_response(request)


# Redirect origin.givefood.org.uk to www.givefood.org.uk
# if the appname is not gfoffline
class RedirectToWWW:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        if (request.get_host() == "origin.givefood.org.uk" and
                resolve(request.path).app_name != "gfoffline"):
            new_url = request.build_absolute_uri().replace(
                "origin.givefood.org.uk", "www.givefood.org.uk", 1
            )
            return redirect(new_url, permanent=True)

        return self.get_response(request)


# Add Link header for GeoJSON preloading based on the view
class GeoJSONPreload:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Only add Link header for successful HTML responses
        if (response.status_code == 200 and
                'text/html' in response.get('Content-Type', '')):
            url_name = None
            try:
                resolved = resolve(request.path)
                url_name = resolved.url_name
                slug = resolved.kwargs.get('slug')
            except Exception:
                pass

            # Determine which geojson URL to preload based on the view
            geojson_url = None

            if url_name == 'index':
                # Main index page uses the general geojson
                geojson_url = reverse('wfbn:geojson')
            elif url_name in [
                'foodbank', 'foodbank_locations',
                'foodbank_donationpoints', 'foodbank_location'
            ]:
                # Foodbank-specific pages use foodbank geojson
                if slug:
                    geojson_url = reverse(
                        'wfbn:foodbank_geojson', kwargs={'slug': slug}
                    )
            elif url_name == 'foodbank_nearby':
                # Nearby page uses the general geojson
                geojson_url = reverse('wfbn:geojson')
            elif url_name == 'constituency':
                # Constituency page uses constituency geojson
                parlcon_slug = resolved.kwargs.get('slug')
                if parlcon_slug:
                    geojson_url = reverse(
                        'wfbn:constituency_geojson',
                        kwargs={'parlcon_slug': parlcon_slug}
                    )

            # Add Link header if we have a geojson URL to preload
            if geojson_url:
                link_header = (
                    f'<{geojson_url}>; rel=preload; '
                    f'as=fetch; crossorigin=anonymous'
                )
                response['Link'] = link_header

        return response
