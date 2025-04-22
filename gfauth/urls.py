from django.urls import path
from . import views

app_name = "gfauth"

urlpatterns = [
    path('', views.sign_in, name='sign_in'),
    path('sign-out/', views.sign_out, name='sign_out'),
    path('receiver/', views.auth_receiver, name='auth_receiver'),
]