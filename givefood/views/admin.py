from django.shortcuts import render_to_response, get_object_or_404


def admin_index(request):

    template_vars = {}
    return render_to_response("admin_index.html", template_vars)
