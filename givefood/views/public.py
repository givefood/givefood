from django.shortcuts import render_to_response, get_object_or_404


def public_index(request):

    template_vars = {}
    return render_to_response("public/index.html", template_vars)
