# coding: utf-8
import urllib
import mimetypes
import re
import threading

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation
from django.core.urlresolvers import reverse
from django.core.files.base import File
from django.core.files.storage import Storage
from django.core.files.uploadedfile import UploadedFile
from django.core.files.uploadhandler import FileUploadHandler, \
    StopFutureHandlers
from django.http import HttpResponse
from django.utils.encoding import smart_str, force_unicode
from django.test.client import encode_multipart, MULTIPART_CONTENT, BOUNDARY
from djangae.db import transaction

from google.appengine.api import urlfetch
from google.appengine.api import app_identity
from google.appengine.api.images import (
    get_serving_url,
    NotImageError,
    BlobKeyRequiredError,
    TransformationError,
)
from google.appengine.ext.blobstore import (
    BlobInfo,
    BlobKey,
    delete,
    BLOB_KEY_HEADER,
    BLOB_RANGE_HEADER,
    BlobReader,
    create_gs_key,
    create_upload_url,
)

try:
    import cloudstorage
    has_cloudstorage = True
except ImportError:
    has_cloudstorage = False

BUCKET_KEY = 'CLOUD_STORAGE_BUCKET'
DEFAULT_CONTENT_TYPE = 'application/binary'

CACHE_LOCK = threading.Lock()
KEY_CACHE = {}
KEY_CACHE_LIST = []
MAX_KEY_CACHE_SIZE = 500

def _add_to_cache(blob_key_or_info, blob_key, file_info):
    """
        This helps remove overhead when serving cloud storage files
        by caching the results of the RPC calls. We maintain a list of the
        order in which keys were added so that we remove the first key
        when we run out of room. This could be improved by limiting based on
        usage frequency.
    """

    global KEY_CACHE
    global KEY_CACHE_LIST
    global CACHE_LOCK

    with CACHE_LOCK:
        if blob_key_or_info in KEY_CACHE:
            return

        KEY_CACHE_LIST.append(blob_key_or_info)
        KEY_CACHE[blob_key_or_info] = (blob_key, file_info)

        # Truncate the cache size if necessary
        if len(KEY_CACHE_LIST) == MAX_KEY_CACHE_SIZE:
            first = KEY_CACHE_LIST[0]
            KEY_CACHE_LIST = KEY_CACHE_LIST[1:]
            del KEY_CACHE[first]


def _get_from_cache(blob_key_or_info):
    with CACHE_LOCK:
        return KEY_CACHE.get(blob_key_or_info)


def serve_file(request, blob_key_or_info, as_download=False, content_type=None, filename=None, offset=None, size=None):
    """
        Serves a file from the blobstore, reads most of the data from the blobinfo by default but you can override stuff
        by passing kwargs.

        You can also pass a Google Cloud Storage filename as `blob_key_or_info` to use Blobstore API to serve the file:
        https://cloud.google.com/appengine/docs/python/blobstore/#Python_Using_the_Blobstore_API_with_Google_Cloud_Storage
    """

    if isinstance(blob_key_or_info, BlobKey):
        info = BlobInfo.get(blob_key_or_info)
        blob_key = blob_key_or_info
    elif isinstance(blob_key_or_info, basestring):
        info = BlobInfo.get(BlobKey(blob_key_or_info))
        blob_key = BlobKey(blob_key_or_info)
    elif isinstance(blob_key_or_info, BlobInfo):
        info = blob_key_or_info
        blob_key = info.key()
    else:
        raise ValueError("Invalid type %s" % blob_key_or_info.__class__)

    if info == None:
        # Lack of blobstore_info means this is a Google Cloud Storage file
        if has_cloudstorage:
            cached_value = _get_from_cache(blob_key_or_info)
            if cached_value:
                blob_key, info = cached_value
            else:
                info = cloudstorage.stat(blob_key_or_info)
                info.size = info.st_size
                blob_key = create_gs_key('/gs{0}'.format(blob_key_or_info))
                _add_to_cache(blob_key_or_info, blob_key, info)
        else:
            raise ImportError("To serve a Cloud Storage file you need to install cloudstorage")

    response = HttpResponse(content_type=content_type or info.content_type)
    response[BLOB_KEY_HEADER] = str(blob_key)
    response['Accept-Ranges'] = 'bytes'
    http_range = request.META.get('HTTP_RANGE')

    if offset or size:
        # Looks a little bonkers, but basically create the HTTP range string, we cast to int first to make sure
        # nothing funky gets into the headers
        http_range = "{}-{}".format(
            str(int(offset)) if offset else "",
            str(int(offset or 0) + size) if size else ""
        )

    if http_range is not None:
        response[BLOB_RANGE_HEADER] = http_range

    if as_download:
        response['Content-Disposition'] = smart_str(
            u'attachment; filename="%s"' % (filename or info.filename)
        )
    elif filename:
        raise ValueError("You can't specify a filename without also specifying as_download")

    if info.size is not None:
        response['Content-Length'] = info.size
    return response


def get_bucket_name():
    """
        Returns the bucket name for Google Cloud Storage, either from your
        settings or the default app bucket.
    """
    bucket = getattr(settings, BUCKET_KEY, None)
    if not bucket:
        # No explicit setting, lets try the default bucket for your application.
        bucket = app_identity.get_default_gcs_bucket_name()
    if not bucket:
        from django.core.exceptions import ImproperlyConfigured
        message = '%s not set or no default bucket configured' % BUCKET_KEY
        raise ImproperlyConfigured(message)
    return bucket


class BlobstoreUploadMixin():

    def _upload_to_blobstore(self, name, content):
        # With the files api deprecated, we provide a workaround here, an inline upload
        # to the blobstore, using the djangae.views.internalupload handler to return the blob key

        # `encode_multipart()` expects files to have a `name`, even though
        # they’re optional
        if not content.name:
            content.name = 'untitled'

        url = self._create_upload_url()

        response = urlfetch.fetch(url=url,
            payload=encode_multipart(BOUNDARY, {'file': content}),
            method=urlfetch.POST,
            deadline=60,
            follow_redirects=False,
            headers={'Content-Type': MULTIPART_CONTENT}
        )
        if response.status_code != 200:
            raise ValueError("The internal upload to blobstore failed, check the app's logs.")
        return '%s/%s' % (response.content, name.lstrip('/'))


class BlobstoreStorage(Storage, BlobstoreUploadMixin):
    """Google App Engine Blobstore storage backend."""

    def _open(self, name, mode='rb'):
        return BlobstoreFile(name, mode, self)

    def _save(self, name, content):
        name = name.replace('\\', '/')
        if hasattr(content, 'file') and \
           hasattr(content.file, 'blobstore_info'):
            data = content.file.blobstore_info
        elif hasattr(content, 'blobstore_info'):
            data = content.blobstore_info
        elif isinstance(content, File):
            return self._upload_to_blobstore(name, content)
        else:
            raise ValueError("The App Engine storage backend only supports "
                             "BlobstoreFile instances or File instances.")

        if isinstance(data, (BlobInfo, BlobKey)):
            # We change the file name to the BlobKey's str() value.
            if isinstance(data, BlobInfo):
                data = data.key()
            return '%s/%s' % (data, name.lstrip('/'))
        else:
            raise ValueError("The App Engine Blobstore only supports "
                             "BlobInfo values. Data can't be uploaded "
                             "directly. You have to use the file upload "
                             "handler.")

    def delete(self, name):
        delete(self._get_key(name))

    def exists(self, name):
        return self._get_blobinfo(name) is not None

    def size(self, name):
        return self._get_blobinfo(name).size

    def url(self, name):
        try:
            # Return a protocol-less URL, because django can't/won't pass
            # down an argument saying whether it should be secure or not
            url = get_serving_url(self._get_blobinfo(name))
            return re.sub("http://", "//", url)
        except (NotImageError, BlobKeyRequiredError, TransformationError):
            return None

    def created_time(self, name):
        return self._get_blobinfo(name).creation

    def get_valid_name(self, name):
        return force_unicode(name).strip().replace('\\', '/')

    def get_available_name(self, name, max_length=None):
        ret = name.replace('\\', '/')
        if max_length and len(ret) > max_length:
            raise SuspiciousFileOperation()
        return ret

    def _get_key(self, name):
        return BlobKey(name.split('/', 1)[0])

    def _get_blobinfo(self, name):
        return BlobInfo.get(self._get_key(name))

    def _create_upload_url(self):
        # Creating the upload URL can't be atomic, otherwise the session
        # key will not be consistent when uploading the file
        with transaction.non_atomic():
            return create_upload_url(reverse('djangae_internal_upload_handler'))


class CloudStorage(Storage, BlobstoreUploadMixin):
    """
        Google Cloud Storage backend, set this as your default backend
        for ease of use, you can specify and non-default bucket in the
        constructor.

        You can modify objects access control by changing google_acl
        attribute to one of mentioned by docs (XML column):
        https://cloud.google.com/storage/docs/access-control?hl=en#predefined-acl
    """
    write_options = None

    def __init__(self, bucket=None, google_acl=None):
        if not bucket:
            bucket = get_bucket_name()
        self.bucket = bucket
        # +2 for the slashes.
        self._bucket_prefix_len = len(bucket) + 2
        if cloudstorage.common.local_run() and not cloudstorage.common.get_access_token():
            # We do it this way so that the stubs override in tests
            self.api_url = '/_ah/gcs'
        else:
            self.api_url = 'https://storage.googleapis.com'

        self.write_options = self.__class__.write_options or {}
        if google_acl:
            # If you don't specify an acl means you get the default permissions.
            self.write_options['x-goog-acl'] = google_acl

    def url(self, filename):
        quoted_filename = urllib.quote(self._add_bucket(filename))
        return '{0}{1}'.format(self.api_url, quoted_filename)

    def _open(self, name, mode='r'):
        # Handle 'rb' as 'r'.
        mode = mode[:1]
        fp = cloudstorage.open(self._add_bucket(name), mode=mode)
        return File(fp)

    def get_valid_name(self, name):
        # App Engine doesn't properly deal with "./" and a blank upload_to argument
        # on a filefield results in ./filename so we must remove it if it's there.
        if name.startswith("./"):
            name = name.replace("./", "", 1)
        return name

    def _add_bucket(self, name):
        safe_name = urllib.quote(name.encode('utf-8'))
        return '/{0}/{1}'.format(self.bucket, safe_name)

    def _content_type_for_name(self, name):
        # guess_type returns (None, encoding) if it can't guess.
        return mimetypes.guess_type(name)[0] or DEFAULT_CONTENT_TYPE

    def _save(self, name, content):
        name = self.get_valid_name(name) #Make sure the name is valid

        kwargs = {
            'content_type': self._content_type_for_name(name),
            'options': self.write_options,
        }
        with cloudstorage.open(self._add_bucket(name), 'w', **kwargs) as fp:
            fp.write(content.read())
        return name

    def delete(self, name):
        try:
            cloudstorage.delete(self._add_bucket(name))
        except cloudstorage.NotFoundError:
            pass

    def exists(self, name):
        size = self.size(name)
        return size is not None

    def size(self, name):
        try:
            info = cloudstorage.stat(self._add_bucket(name))
        except cloudstorage.NotFoundError:
            return None
        else:
            return info.st_size

    def _create_upload_url(self):
        return create_upload_url(
            reverse('djangae_internal_upload_handler'),
            gs_bucket_name=self.bucket_name
        )

class UniversalNewLineBlobReader(BlobReader):
    def readline(self, size=-1):
        limit_size = size > -1

        buf = []  # A buffer to store our line
        #Read characters until we find a \r or \n, or hit the maximum size
        c = self.read(size=1)
        while c != '\n' and c != '\r' and (not limit_size or len(buf) < size):
            if not c:
                break

            buf.append(c)
            c = self.read(size=1)

        # If we found a \r, it could be "\r\n" so read the next char
        if c == '\r':
            n = self.read(size=1)

            #If the \r wasn't followed by a \n, then it was a mac line ending
            #so we seek backwards 1
            if n and n != '\n':
                #We only check n != '\n' if we weren't EOF (e.g. n evaluates to False) otherwise
                #we'd read nothing, and then seek back 1 which would then be re-read next loop etc.
                self.seek(-1, 1)  # The second 1 means to seek relative to the current position

        # Only add a trailing \n (if it doesn't break the size constraint)
        if buf and (not limit_size or len(buf) < size):
            buf.append("\n")  # Add our trailing \n, no matter what the line endings were

        return "".join(buf)


class BlobstoreFile(File):

    def __init__(self, name, mode, storage):
        self.name = name
        self._storage = storage
        self._mode = mode
        self.blobstore_info = storage._get_blobinfo(name)

    @property
    def size(self):
        return self.blobstore_info.size

    def write(self, content):
        raise NotImplementedError()

    @property
    def file(self):
        if not hasattr(self, '_file'):
            self._file = UniversalNewLineBlobReader(self.blobstore_info.key())
        return self._file


class BlobstoreFileUploadHandler(FileUploadHandler):
    """
    File upload handler for the Google App Engine Blobstore.
    """
    def __init__(self, request=None):
        super(BlobstoreFileUploadHandler, self).__init__(request)
        self.blobkey = None

    def new_file(self, field_name, file_name, content_type, content_length, charset=None, content_type_extra=None):
        if content_type_extra:
            self.blobkey = content_type_extra.get('blob-key')

        if self.blobkey:
            self.blobkey = BlobKey(self.blobkey)
            raise StopFutureHandlers()
        else:
            return super(BlobstoreFileUploadHandler, self).new_file(field_name, file_name, content_type, content_length, charset)

    def receive_data_chunk(self, raw_data, start):
        """
        Add the data to the StringIO file.
        """
        if not self.blobkey:
            return raw_data

    def file_complete(self, file_size):
        """
        Return a file object if we're activated.
        """
        if not self.blobkey:
            return

        return BlobstoreUploadedFile(
            blobinfo=BlobInfo(self.blobkey),
            charset=self.charset)


class BlobstoreUploadedFile(UploadedFile):
    """
    A file uploaded into memory (i.e. stream-to-memory).
    """

    def __init__(self, blobinfo, charset):
        super(BlobstoreUploadedFile, self).__init__(
            UniversalNewLineBlobReader(blobinfo.key()), blobinfo.filename,
            blobinfo.content_type, blobinfo.size, charset)
        self.blobstore_info = blobinfo

    def open(self, mode=None):
        pass

    def chunks(self, chunk_size=1024 * 128):
        self.file.seek(0)
        while True:
            content = self.read(chunk_size)
            if not content:
                break
            yield content

    def multiple_chunks(self, chunk_size=1024 * 128):
        return True
