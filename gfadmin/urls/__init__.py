#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Re-assembles the admin URLconf from per-domain submodules so that
`include('gfadmin.urls', namespace="admin")` keeps working unchanged after the
split of the original flat `urls.py` into a `urls/` package.

Patterns are concatenated in the order below. Overlapping patterns (where
matching is order-sensitive) always live within a single submodule, so this
concatenation order is safe.
"""

from gfadmin.urls.core import urlpatterns as core_urls
from gfadmin.urls.foodbanks import urlpatterns as foodbanks_urls
from gfadmin.urls.orders import urlpatterns as orders_urls
from gfadmin.urls.needs import urlpatterns as needs_urls
from gfadmin.urls.items import urlpatterns as items_urls
from gfadmin.urls.geography import urlpatterns as geography_urls
from gfadmin.urls.credentials import urlpatterns as credentials_urls
from gfadmin.urls.subscriptions import urlpatterns as subscriptions_urls
from gfadmin.urls.stats import urlpatterns as stats_urls
from gfadmin.urls.crawl_sets import urlpatterns as crawl_sets_urls
from gfadmin.urls.testers import urlpatterns as testers_urls

app_name = "gfadmin"

urlpatterns = (
    core_urls
    + foodbanks_urls
    + orders_urls
    + needs_urls
    + items_urls
    + geography_urls
    + credentials_urls
    + subscriptions_urls
    + stats_urls
    + crawl_sets_urls
    + testers_urls
)
