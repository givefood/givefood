
AUTHENTICATION_BACKENDS = (
    'djangae.contrib.gauth.datastore.backends.AppEngineUserAPIBackend',
)

AUTH_USER_MODEL = 'djangae.GaeDatastoreUser'
LOGIN_URL = 'djangae_login_redirect'

# Set this to True to allow unknown Google users to sign in. Matching is done
# by email. Defaults to False.
# DJANGAE_CREATE_UNKNOWN_USER = False
