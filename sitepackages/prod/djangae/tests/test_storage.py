# coding: utf-8
import httplib
import os
import urlparse
from unittest import skipIf

from google.appengine.api import urlfetch
from google.appengine.api.images import TransformationError

from django.core.files.base import File, ContentFile
from django.test.utils import override_settings

from djangae.contrib import sleuth
from djangae.storage import BlobstoreStorage, CloudStorage, has_cloudstorage
from djangae.test import TestCase


@skipIf(not has_cloudstorage, "Cloud Storage not available")
class CloudStorageTests(TestCase):

    @override_settings(CLOUD_STORAGE_BUCKET='test_bucket')
    def test_basic_actions(self):
        storage = CloudStorage()
        name = u'tmp.ąćęłńóśźż.马铃薯.zip'

        f = ContentFile('content', name='my_file')
        filename = storage.save(name, f)
        self.assertIsInstance(filename, basestring)
        self.assertTrue(filename.endswith(name))

        self.assertTrue(storage.exists(filename))
        self.assertEqual(storage.size(filename), len('content'))
        url = storage.url(filename)
        self.assertIsInstance(url, basestring)
        self.assertNotEqual(url, '')

        abs_url = urlparse.urlunparse(
            ('http', os.environ['HTTP_HOST'], url, None, None, None)
        )
        response = urlfetch.fetch(abs_url)
        self.assertEqual(response.status_code, httplib.OK)
        self.assertEqual(response.content, 'content')

        f = storage.open(filename)
        self.assertIsInstance(f, File)
        self.assertEqual(f.read(), 'content')

        # Delete it
        storage.delete(filename)
        self.assertFalse(storage.exists(filename))

    @override_settings(CLOUD_STORAGE_BUCKET='test_bucket')
    def test_dotslash_prefix(self):
        storage = CloudStorage()
        name = './my_file'
        f = ContentFile('content')
        filename = storage.save(name, f)
        self.assertEqual(filename, name.lstrip("./"))

    @override_settings(CLOUD_STORAGE_BUCKET='test_bucket')
    def test_supports_nameless_files(self):
        storage = CloudStorage()
        f2 = ContentFile('nameless-content')
        storage.save('tmp2', f2)

    @override_settings(CLOUD_STORAGE_BUCKET='test_bucket')
    def test_new_objects_get_the_default_acl(self):
        storage = CloudStorage()
        filename = 'example.txt'
        fileobj = ContentFile('content', name=filename)

        with sleuth.watch('cloudstorage.open') as open_func:
            storage.save(filename, fileobj)

        self.assertTrue(storage.exists(filename))
        # There's no x-goog-acl argument, so default perms are applied.
        self.assertEqual(open_func.calls[0].kwargs['options'], {})

    @override_settings(CLOUD_STORAGE_BUCKET='test_bucket')
    def test_new_objects_with_an_explicit_acl(self):
        storage = CloudStorage(google_acl='public-read')
        filename = 'example.txt'
        fileobj = ContentFile('content', name=filename)

        with sleuth.watch('cloudstorage.open') as open_func:
            storage.save(filename, fileobj)

        self.assertTrue(storage.exists(filename))
        self.assertEqual(
            open_func.calls[0].kwargs['options'],
            {'x-goog-acl': 'public-read'},
        )


class BlobstoreStorageTests(TestCase):
    def test_basic_actions(self):

        storage = BlobstoreStorage()

        # Save a new file
        f = ContentFile('content', name='my_file')
        filename = storage.save('tmp', f)

        self.assertIsInstance(filename, basestring)
        self.assertTrue(filename.endswith('tmp'))

        # Check .exists(), .size() and .url()
        self.assertTrue(storage.exists(filename))
        self.assertEqual(storage.size(filename), len('content'))
        url = storage.url(filename)
        self.assertIsInstance(url, basestring)
        self.assertNotEqual(url, '')

        # Check URL can be fetched
        abs_url = urlparse.urlunparse(
            ('http', os.environ['HTTP_HOST'], url, None, None, None)
        )
        response = urlfetch.fetch(abs_url)
        self.assertEqual(response.status_code, httplib.OK)
        self.assertEqual(response.content, 'content')

        # Open it, read it
        # NOTE: Blobstore doesn’t support updating existing files.
        f = storage.open(filename)
        self.assertIsInstance(f, File)
        self.assertEqual(f.read(), 'content')

        # Delete it
        storage.delete(filename)
        self.assertFalse(storage.exists(filename))

    def test_supports_nameless_files(self):
        storage = BlobstoreStorage()
        f2 = ContentFile('nameless-content')
        storage.save('tmp2', f2)

    def test_transformation_error(self):
        storage = BlobstoreStorage()
        with sleuth.detonate('djangae.storage.get_serving_url', TransformationError):
            self.assertIsNone(storage.url('thing'))
