from django.urls import path, re_path
from gfadmin.views import *

urlpatterns = [

    path("", index, name="index"),

    path("slug-redirects/", slug_redirects, name="slug_redirects"),
    path("slug-redirect/new/", slug_redirect_form, name="slug_redirect_new"),
    path("slug-redirect/<int:id>/edit/", slug_redirect_form, name="slug_redirect_form"),

    path("settings/", settings, name="settings"),
    path("map/", admin_map, name="map"),

    path("search/", search_results, name="search_results"),

    path("clearcache/", clearcache, name="clearcache"),

    path("proxy/", proxy, name="proxy"),
    re_path(r'^proxy/gmaps/(?P<type>textsearch|placedetails)/$', gmap_proxy, name="gmap_proxy"),

    path("frag/<slug:frag>/", frag, name="frag"),

    path("article/<int:article_id>/toggle-featured/", article_toggle_featured, name="article_toggle_featured"),

]
