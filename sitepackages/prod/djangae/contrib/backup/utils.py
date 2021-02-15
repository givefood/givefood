import datetime

from django.conf import settings
from google.appengine.api import app_identity


SETTINGS_PREFIX = "DJANGAE_BACKUP_"


def get_backup_setting(name, required=True, default=None):
    settings_name = "{}{}".format(SETTINGS_PREFIX, name)
    if required and not hasattr(settings, settings_name):
        raise Exception("{} is required".format(settings_name))

    return getattr(settings, settings_name, default)


def get_gcs_bucket():
    """Get a bucket from DJANGAE_BACKUP_GCS_BUCKET setting. Defaults to the
    default application bucket with 'djangae-backups' appended.

    Raises an exception if DJANGAE_BACKUP_GCS_BUCKET is missing and there is
    no default bucket.
    """
    # we don't use `get_backup_setting` here as default would be a callable
    # redundantly called if the setting was specified.
    try:
        bucket = settings.DJANGAE_BACKUP_GCS_BUCKET
    except AttributeError:
        bucket = app_identity.get_default_gcs_bucket_name()

        if bucket:
            bucket = '{}/djangae-backups'.format(bucket)

    if not bucket:
        raise Exception('No DJANGAE_BACKUP_GCS_BUCKET or default bucket')

    return bucket


def get_backup_path(bucket=None):
    """
    Returns the full path to write the backup to in GCS. This looks
    something like 
    `gs://example.appspot.com/scheduled-backups/2018-20-10/202059`

    Bucket can be provided as a kwarg (e.g. passed in from a GET param),
    otherwise we fallback to the `DJANGAE_BACKUP_GCS_BUCKET` setting.
    """
    bucket = bucket if bucket else get_gcs_bucket()
    dt = datetime.datetime.utcnow()
    return 'gs://{}/{:%Y%m%d}/{:%H%M%S}'.format(bucket, dt, dt)
