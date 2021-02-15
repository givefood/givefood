import logging

from django.http import HttpResponse
from djangae.environment import task_or_admin_only

from .tasks import backup_datastore
from .utils import get_backup_setting


logger = logging.getLogger(__name__)


@task_or_admin_only
def create_datastore_backup(request):
    """
    Handler which triggers a datastore backup if DJANGAE_BACKUP_ENABLED set.
    
    GET params can be passed to override the default bucket target and entity
    kinds to backup. This allows us to have different types of backup and not
    be constrained by the settings config (e.g. we might have different cron
    jobs which run at different intervals that each require different entity
    requirements).
    """
    backup_enabled = get_backup_setting("ENABLED", False)

    if backup_enabled:
        bucket = request.GET.get('bucket')
        kinds = request.GET.getlist('kind') or None

        # there isn't much overhead of calling this within the request cycle...
        backup_datastore(bucket=bucket, kinds=kinds)

        msg = "Scheduled backup of datastore started."
        logger.info(msg)
    else:
        msg = "DJANGAE_BACKUP_ENABLED is False. Not backing up."
        logger.warning("DJANGAE_BACKUP_ENABLED is False. Not backing up.")

    return HttpResponse(msg)
