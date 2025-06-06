import time

from django.contrib.auth.views import redirect_to_login
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.urls import resolve

from givefood.func import get_cred

# Inject the render time into the response content
def RenderTime(get_response):
    def middleware(request):
        t1 = time.time()
        response = get_response(request)
        t2 = time.time()
        duration = t2 - t1
        duration = round(duration * 1000, 3)
        response.content = response.content.replace(b"PUTTHERENDERTIMEHERE", bytes(str(duration), "utf-8"), 1)
        return response
    return middleware


class OfflineKeyCheck:

    key_check_apps = ["gfoffline",]

    def __init__(self, get_response):
       self.get_response = get_response

    def __call__(self, request):
        
        if resolve(request.path).app_name in self.key_check_apps:

            key = request.GET.get("key", None)
            if key != get_cred("offline_key"):
                return HttpResponseForbidden("Invalid key")
            

        return self.get_response(request)


# Middleware to check if the user is logged in for specific apps
class LoginRequiredAccess:

   login_apps = ["gfadmin",]

   def __init__(self, get_response):
       self.get_response = get_response

   def __call__(self, request):
        
        if resolve(request.path).app_name in self.login_apps:

            try:
                user_email = request.session.get("user_data").get("email")
                email_verified = request.session.get("user_data").get("email_verified")
                hosted_domain = request.session.get("user_data").get("hd")
            except AttributeError:
                return redirect("auth:sign_in")
            
            if not email_verified or hosted_domain != "givefood.org.uk":
                return redirect("auth:sign_in")

        return self.get_response(request)