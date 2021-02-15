import logging
import os

from google.appengine.api import app_identity

from google.auth import app_engine
from google.oauth2 import service_account
import googleapiclient.discovery

from django.apps import apps

from djangae.environment import is_production_environment

from .utils import get_backup_setting, get_backup_path


logger = logging.getLogger(__name__)


AUTH_SCOPES = ['https://www.googleapis.com/auth/datastore']
SERVICE_URL = 'https://datastore.googleapis.com/$discovery/rest?version=v1'


def backup_datastore(bucket=None, kinds=None):
    """
    Using the new scheduled backup service write all required entity kinds
    to a specific GCS bucket path.
    """
    backup_enabled = get_backup_setting("ENABLED", False)
    if not backup_enabled:
        logger.warning(
            "DJANGAE_BACKUP_ENABLED is False or not set."
            "The datastore backup will not be run."
        )
        return

    # make sure no blacklisted entity kinds are included in our export
    valid_models = _get_valid_export_models(kinds)
    if not valid_models:
        logger.warning("No whitelisted entity kinds to export.")
        return

    # build the service object with the necessary credentials and trigger export
    service = _get_service()
    body = {
        'outputUrlPrefix': get_backup_path(bucket),
        'entityFilter': {
            'kinds': valid_models,
        }
    }
    app_id = app_identity.get_application_id()
    request = service.projects().export(projectId=app_id, body=body)
    request.execute()


def _get_valid_export_models(kinds=None):
    """Make sure no blacklist models are included in our backup export."""
    excluded_models = get_backup_setting("EXCLUDE_MODELS", required=False, default=[])
    excluded_apps = get_backup_setting("EXCLUDE_APPS", required=False, default=[])

    models_to_backup = []
    for model in apps.get_models(include_auto_created=True):
        app_label = model._meta.app_label
        object_name = model._meta.object_name
        model_def = "{}_{}".format(app_label, object_name.lower())

        if app_label in excluded_apps:
            logger.info(
                "Not backing up %s due to the %s app being in DJANGAE_BACKUP_EXCLUDE_APPS",
                model_def, app_label
            )
            continue

        if model_def in excluded_models:
            logger.info(
                "Not backing up %s as it is blacklisted in DJANGAE_BACKUP_EXCLUDE_MODELS",
                model_def
            )
            continue

        logger.info("%s added to list of models to backup", model_def)
        models_to_backup.append(model_def)

    # if kinds we explcitly provided by the caller, we only return those
    # already validated by our previous checks
    if kinds:
        models_to_backup = [model for model in models_to_backup if model in kinds]

    return models_to_backup


def _get_service():
    """Creates an Admin API service object for talking to the API."""
    credentials = _get_authentication_credentials()
    return googleapiclient.discovery.build(
        'admin', 'v1',
        credentials=credentials,
        discoveryServiceUrl=SERVICE_URL
    )


def _get_authentication_credentials():
    """
    Returns authentication credentials depending on environment. See
    https://developers.google.com/api-client-library/python/auth/service-accounts
    """
    if is_production_environment():
        credentials = app_engine.Credentials(scopes=AUTH_SCOPES)
    else:
        service_account_path = os.environ['GOOGLE_APPLICATION_CREDENTIALS']
        credentials = service_account.Credentials.from_service_account_file(
            service_account_path, scopes=AUTH_SCOPES
        )
    return credentials
