from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from google.oauth2 import id_token
from google.auth.transport import requests
from django.views.decorators.cache import never_cache

@csrf_exempt
@never_cache
def sign_in(request):
    return render(request, 'auth/sign_in.html')

@csrf_exempt
def auth_receiver(request):
    token = request.POST['credential']

    try:
        user_data = id_token.verify_oauth2_token(
            token, requests.Request(), "927281004707-tboi1tsphl4bgtqn72e76rmc7r2q22tk.apps.googleusercontent.com"
        )
    except ValueError:
        return HttpResponse(status=403)

    request.session['user_data'] = user_data

    return redirect('auth:sign_in')

def sign_out(request):
    del request.session['user_data']
    return redirect('auth:sign_in')