#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Re-exports every public model under its original name so existing imports
(`from givefood.models import Foo`) keep working unchanged after the split
into a `models/` package.
"""

from givefood.models.analytics import CrawlItem, CrawlSet, FoodbankHit
from givefood.models.articles import FoodbankArticle
from givefood.models.foodbank import (
    Foodbank, FoodbankDonationPoint, FoodbankLocation,
)
from givefood.models.geo import Place, PlacePhoto, Postcode
from givefood.models.needs import (
    FoodbankChange, FoodbankChangeLine, FoodbankChangeTranslation,
    FoodbankDiscrepancy,
)
from givefood.models.operations import CharityYear, Dump, GfCredential, SlugRedirect
from givefood.models.orders import Order, OrderGroup, OrderItem, OrderLine
from givefood.models.political import ParliamentaryConstituency
from givefood.models.subscribers import (
    ConstituencySubscriber, FoodbankSubscriber, MobileSubscriber,
    WebPushSubscription, WhatsappSubscriber,
)

__all__ = [
    "CharityYear",
    "ConstituencySubscriber",
    "CrawlItem",
    "CrawlSet",
    "Dump",
    "Foodbank",
    "FoodbankArticle",
    "FoodbankChange",
    "FoodbankChangeLine",
    "FoodbankChangeTranslation",
    "FoodbankDiscrepancy",
    "FoodbankDonationPoint",
    "FoodbankHit",
    "FoodbankLocation",
    "FoodbankSubscriber",
    "GfCredential",
    "MobileSubscriber",
    "Order",
    "OrderGroup",
    "OrderItem",
    "OrderLine",
    "ParliamentaryConstituency",
    "Place",
    "PlacePhoto",
    "Postcode",
    "SlugRedirect",
    "WebPushSubscription",
    "WhatsappSubscriber",
]
