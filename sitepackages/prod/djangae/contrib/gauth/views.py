# STANDARD LIB
import hashlib

# 3RD PARTY
from django.contrib.auth import logout as django_logout
from django.http import HttpResponseRedirect
from django.utils.encoding import iri_to_uri
from google.appengine.api import users


def login_redirect(request):
    return HttpResponseRedirect(users.create_login_url(dest_url=request.GET.get('next')))


def switch_accounts(request):
    """ A view which allows a user to change which of their Google accounts they're logged in with.

        The URL for the user to be sent to afterwards should be provided in request.GET['next'].

        See https://p.ota.to/blog/2014/2/google-multiple-sign-in-on-app-engine/

        For the account switching, the user needs to go first to Google's login page. If he/she
        gets back with the same user, we send them to the logout URL and *then* the login page.

        Scenario:
        1. User clicks a 'switch accounts' link which takes them to this view.
        2. We redirect them to the Google login screen where - if they are logged into multiple
            accounts - they get the opportunity to switch account.
        3. Two things may happen:
           a. They aren't logged into multiple accounts, so Google redirects them straight back to
              us. As we want them to switch account, we send them back to Google's logout URL with
              the `continue` url set to the Google login page. => They log into another account.
              i. They then return to here, where we clear their session and send them on their way.
           b. They actually switched account, and so they come back with a different account and we
              redirect them to the original destination set when first visiting this view.

        See the steps in the code, referring to the steps of the scenario.
    """
    destination = request.GET.get('next', '/')
    current_google_user = users.get_current_user()
    # Just making sure we don't save readable info in the session as we can't be sure this session
    # will be terminated after logout. This is possibly paranoia.
    user_hash = hashlib.sha1(current_google_user.user_id()).hexdigest()
    previous_user_hash = request.session.get('previous_user')
    if previous_user_hash:
        if user_hash == previous_user_hash:
            # Step 3.a.
            django_logout(request)  # Make sure old Django user session gets flushed.
            request.session['previous_user'] = user_hash # but add the previous_user hash back in
            # We want to create a URL to the logout URL which then goes to the login URL which then
            # goes back to *this* view, which then goes to the final destination
            login_url = iri_to_uri(users.create_login_url(request.get_full_path()))
            logout_url = users.create_logout_url(login_url)
            return HttpResponseRedirect(logout_url)
        else:
            # Step 3.b, or step 2.a.i.
            del request.session['previous_user']
            return HttpResponseRedirect(destination)
    else:
        # Step 2:
        switch_account_url = iri_to_uri(request.get_full_path())
        redirect_url = users.create_login_url(switch_account_url)
        django_logout(request)  # Make sure old Django user session gets flushed.
        request.session['previous_user'] = user_hash
        return HttpResponseRedirect(redirect_url)
