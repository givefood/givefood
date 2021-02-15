from django.test import override_settings
from djangae.test import TestCase, RequestFactory
from djangae.contrib import sleuth

from ..views import create_datastore_backup


class DatastoreBackupViewTestCase(TestCase):
    """Tests for djangae.contrib.backup.views"""

    @override_settings(DJANGAE_BACKUP_ENABLED=False)
    @sleuth.switch('djangae.environment.is_in_task', lambda: True)
    def test_flag_prevents_backup(self):
        request = RequestFactory().get('/')

        with sleuth.watch('djangae.contrib.backup.views.backup_datastore') as backup_fn:
            create_datastore_backup(request)
            self.assertFalse(backup_fn.called)

    @override_settings(DJANGAE_BACKUP_ENABLED=True)
    @sleuth.switch('djangae.environment.is_in_task', lambda: True)
    def test_get_params_propogate(self):
        request = RequestFactory().get('/?kind=django_admin_log&bucket=foobar')
        with sleuth.watch('djangae.contrib.backup.views.backup_datastore') as backup_fn:
            create_datastore_backup(request)
            self.assertTrue(backup_fn.called)
            self.assertEqual(
                backup_fn.calls[0][1],
                {
                    'bucket': 'foobar',
                    'kinds': [u'django_admin_log']
                }
            )
