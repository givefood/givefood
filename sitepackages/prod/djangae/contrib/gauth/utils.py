from django.core.urlresolvers import reverse
from django.utils.encoding import iri_to_uri


def get_switch_accounts_url(request=None, next="/"):
    """ Get the URL for allowing the user to switch which of their many Google accounts they are
        logged in with.
    """
    if request:
        next = request.get_full_path()
    return reverse("djangae_switch_accounts") + "?next=" + iri_to_uri(next)
