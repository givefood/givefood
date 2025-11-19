from datetime import datetime, timedelta

from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.views.decorators.http import require_POST
from django.db.models import Q, Count, Sum

from givefood.models import (
    Foodbank, FoodbankChange, FoodbankDiscrepancy, 
    FoodbankArticle, FoodbankLocation, FoodbankDonationPoint,
    Order, FoodbankHit, CrawlSet, CrawlItem, FoodbankChangeLine,
    FoodbankSubscriber, ParliamentaryConstituency
)
from givefood.forms import FoodbankForm, NeedForm, OrderForm


def index(request):
    """Dashboard with overview of needs, discrepancies, and stats."""
    
    # Needs
    unpublished_needs = FoodbankChange.objects.filter(
        published=False, 
        nonpertinent=False
    ).order_by("-created")[:20]
    
    published_needs = FoodbankChange.objects.filter(
        published=True
    ).order_by("-created")[:20]
    
    # Discrepancies
    discrepancies = FoodbankDiscrepancy.objects.filter(
        status='New'
    ).order_by("-created")[:20]
    
    # Stats
    yesterday = datetime.now() - timedelta(days=1)
    week_ago = datetime.now() - timedelta(days=7)
    
    try:
        latest_need_crawlset = CrawlSet.objects.filter(
            crawl_type="need"
        ).order_by("-start")[:1][0]
    except IndexError:
        latest_need_crawlset = None
    
    stats = {
        "oldest_edit": Foodbank.objects.exclude(is_closed=True).order_by("edited")[:1][0],
        "latest_edit": Foodbank.objects.exclude(is_closed=True).order_by("-edited")[:1][0],
        "sub_count_24h": FoodbankSubscriber.objects.filter(created__gte=yesterday).count(),
        "sub_count_7d": FoodbankSubscriber.objects.filter(created__gte=week_ago).count(),
        "need_count_24h": FoodbankChangeLine.objects.filter(created__gte=yesterday).count(),
        "need_check_24h": CrawlItem.objects.filter(
            crawl_set__crawl_type="need", 
            finish__gte=yesterday
        ).count(),
        "oldest_need_check": Foodbank.objects.exclude(is_closed=True).exclude(
            shopping_list_url__contains="facebook.com"
        ).order_by("last_need_check")[:1][0],
        "latest_need_check": Foodbank.objects.exclude(is_closed=True).exclude(
            last_need_check__isnull=True
        ).order_by("-last_need_check")[:1][0],
        "latest_need_crawlset": latest_need_crawlset,
        "article_check_24h": CrawlItem.objects.filter(
            crawl_set__crawl_type="article", 
            finish__gte=yesterday
        ).count(),
        "charity_check_24h": CrawlItem.objects.filter(
            crawl_set__crawl_type="charity", 
            finish__gte=yesterday
        ).count(),
    }
    
    # Articles
    articles = FoodbankArticle.objects.all().order_by("-published_date")[:20]
    
    template_vars = {
        "unpublished_needs": unpublished_needs,
        "published_needs": published_needs,
        "discrepancies": discrepancies,
        "stats": stats,
        "articles": articles,
        "section": "home",
    }
    return render(request, "admin2/index.html", template_vars)


def foodbanks_list(request):
    """List of all foodbanks with htmx-powered sorting."""
    
    sort = request.GET.get("sort", "edited")
    
    # Build base queryset
    cutoff_date = datetime.now().date() - timedelta(days=28)
    foodbanks = Foodbank.objects.exclude(is_closed=True).annotate(
        hits_last_28_days=Sum(
            'foodbankhit__hits',
            filter=Q(foodbankhit__day__gte=cutoff_date)
        )
    ).order_by(sort)
    
    # For htmx requests, return just the table rows
    if request.headers.get('HX-Request'):
        return render(request, "admin2/includes/foodbank_rows.html", {
            "foodbanks": foodbanks,
        })
    
    template_vars = {
        "foodbanks": foodbanks,
        "sort": sort,
        "section": "foodbanks",
    }
    return render(request, "admin2/foodbanks_list.html", template_vars)


def foodbank_detail(request, slug):
    """Detail view for a single foodbank with htmx tabs."""
    
    foodbank = get_object_or_404(Foodbank, slug=slug)
    
    # Get tab parameter
    tab = request.GET.get("tab", "overview")
    
    counts = {
        "locations": FoodbankLocation.objects.filter(foodbank=foodbank).count(),
        "needs": FoodbankChange.objects.filter(foodbank=foodbank).count(),
        "orders": Order.objects.filter(foodbank=foodbank).count(),
        "donation_points": FoodbankDonationPoint.objects.filter(foodbank=foodbank).count(),
        "articles": FoodbankArticle.objects.filter(foodbank=foodbank).count(),
        "subscribers": FoodbankSubscriber.objects.filter(foodbank=foodbank).count(),
    }
    
    # Load tab-specific data
    context = {
        "foodbank": foodbank,
        "counts": counts,
        "tab": tab,
    }
    
    if tab == "needs":
        context["needs"] = FoodbankChange.objects.filter(
            foodbank=foodbank
        ).order_by("-created")[:50]
    elif tab == "orders":
        context["orders"] = Order.objects.filter(
            foodbank=foodbank
        ).order_by("-created")[:50]
    elif tab == "locations":
        context["locations"] = FoodbankLocation.objects.filter(
            foodbank=foodbank
        ).order_by("name")
    elif tab == "donation_points":
        context["donation_points"] = FoodbankDonationPoint.objects.filter(
            foodbank=foodbank
        ).order_by("name")
    
    # For htmx requests, return just the tab content
    if request.headers.get('HX-Request'):
        return render(request, f"admin2/includes/foodbank_tab_{tab}.html", context)
    
    return render(request, "admin2/foodbank_detail.html", context)


def foodbank_form(request, slug=None):
    """Create or edit a foodbank with htmx validation."""
    
    if slug:
        foodbank = get_object_or_404(Foodbank, slug=slug)
        page_title = f"Edit {foodbank.full_name()}"
    else:
        foodbank = None
        page_title = "New Food Bank"
    
    if request.POST:
        form = FoodbankForm(request.POST, instance=foodbank)
        if form.is_valid():
            foodbank = form.save()
            
            # For htmx, return a redirect header
            if request.headers.get('HX-Request'):
                response = HttpResponse()
                response['HX-Redirect'] = f"/admin2/foodbank/{foodbank.slug}/"
                return response
            
            return redirect("gfadmin2:foodbank_detail", slug=foodbank.slug)
    else:
        form = FoodbankForm(instance=foodbank)
    
    template_vars = {
        "form": form,
        "page_title": page_title,
        "foodbank": foodbank,
    }
    return render(request, "admin2/foodbank_form.html", template_vars)


def needs_list(request):
    """List of needs with htmx filtering."""
    
    filter_type = request.GET.get("filter", "unpublished")
    
    if filter_type == "unpublished":
        needs = FoodbankChange.objects.filter(
            published=False, 
            nonpertinent=False
        ).order_by("-created")[:200]
    elif filter_type == "published":
        needs = FoodbankChange.objects.filter(
            published=True
        ).order_by("-created")[:200]
    elif filter_type == "uncategorised":
        needs = FoodbankChange.objects.filter(
            is_categorised=False
        ).exclude(change_text="Facebook").exclude(
            change_text="Unknown"
        ).exclude(change_text="Nothing").order_by("-created")[:200]
    else:
        needs = FoodbankChange.objects.all().order_by("-created")[:200]
    
    # For htmx requests, return just the table
    if request.headers.get('HX-Request'):
        return render(request, "admin2/includes/needs_table.html", {
            "needs": needs,
        })
    
    template_vars = {
        "needs": needs,
        "filter": filter_type,
        "section": "needs",
    }
    return render(request, "admin2/needs_list.html", template_vars)


def need_detail(request, id):
    """Detail view for a need."""
    
    need = get_object_or_404(FoodbankChange, need_id=id)
    
    template_vars = {
        "need": need,
    }
    return render(request, "admin2/need_detail.html", template_vars)


@require_POST
def need_publish(request, id):
    """Publish or unpublish a need via htmx."""
    
    need = get_object_or_404(FoodbankChange, need_id=id)
    action = request.POST.get("action")
    
    if action == "publish":
        need.published = True
    elif action == "unpublish":
        need.published = False
    
    need.save(do_translate=True)
    
    # For htmx, return updated status
    if request.headers.get('HX-Request'):
        return render(request, "admin2/includes/need_status.html", {
            "need": need,
        })
    
    return redirect("gfadmin2:need_detail", id=id)


@require_POST
def need_delete(request, id):
    """Delete a need via htmx."""
    
    need = get_object_or_404(FoodbankChange, need_id=id)
    need.delete()
    
    # For htmx, return success message
    if request.headers.get('HX-Request'):
        response = HttpResponse()
        response['HX-Redirect'] = '/admin2/'
        return response
    
    return redirect("gfadmin2:index")


def orders_list(request):
    """List of orders with htmx sorting."""
    
    sort = request.GET.get("sort", "delivery_datetime")
    sort_field = f"-{sort}"
    
    orders = Order.objects.all().order_by(sort_field)[:200]
    
    # For htmx requests, return just the table
    if request.headers.get('HX-Request'):
        return render(request, "admin2/includes/orders_table.html", {
            "orders": orders,
        })
    
    template_vars = {
        "orders": orders,
        "sort": sort,
        "section": "orders",
    }
    return render(request, "admin2/orders_list.html", template_vars)


def order_detail(request, id):
    """Detail view for an order."""
    
    order = get_object_or_404(Order, order_id=id)
    
    template_vars = {
        "order": order,
    }
    return render(request, "admin2/order_detail.html", template_vars)


def search(request):
    """Search across all entities with htmx live results."""
    
    query = request.GET.get("q", "").strip()
    
    results = {}
    if query:
        results = {
            "foodbanks": Foodbank.objects.filter(
                Q(name__icontains=query) | 
                Q(address__icontains=query) | 
                Q(postcode__icontains=query)
            )[:20],
            "needs": FoodbankChange.objects.filter(
                Q(change_text__icontains=query) | 
                Q(excess_change_text__icontains=query)
            ).order_by("-created")[:20],
            "locations": FoodbankLocation.objects.filter(
                Q(name__icontains=query) | 
                Q(address__icontains=query) | 
                Q(postcode__icontains=query)
            )[:20],
        }
    
    # For htmx requests, return just the results
    if request.headers.get('HX-Request'):
        return render(request, "admin2/includes/search_results.html", {
            "results": results,
            "query": query,
        })
    
    template_vars = {
        "results": results,
        "query": query,
        "section": "search",
    }
    return render(request, "admin2/search.html", template_vars)
