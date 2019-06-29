from django.conf.urls import url

from djangae.contrib.gauth import views


urlpatterns = [
    url(r'^login_redirect$', views.login_redirect, name='djangae_login_redirect'),
    url(r'^switch_accounts/$', views.switch_accounts, name='djangae_switch_accounts'),
]
