import os
import threading
import logging
import re

blobstore_service = None
server = None

from wsgiref.simple_server import WSGIRequestHandler


class NoLogRequestHandler(WSGIRequestHandler):

    def log_request(self, code='-', size='-'):
        """Normally logs an accepted request. Bug given
        that this is not using global logging but stdout,
        this becomes really annoying in tests. So let's
        not log anything.
        """
        pass


def start_blobstore_service():
    """
        When the blobstore files API was deprecated, the blobstore storage was switched
        to use a POST request to the upload handler when storing files uploaded via Django.

        Unfortunately this breaks in the local sandbox when you aren't running the dev_appserver
        because there is no server to handle the blobstore upload. So, this service is kicked
        off by the local sandbox and only handles blobstore uploads. When runserver kicks in
        this service is stopped.
    """
    global blobstore_service
    global server

    if blobstore_service:
        return

    from wsgiref.simple_server import make_server
    from google.appengine.tools.devappserver2 import blob_upload
    from google.appengine.tools.devappserver2 import blob_image
    from google.appengine.tools.devappserver2 import gcs_server

    from django.core.handlers.wsgi import WSGIRequest
    from django.utils.encoding import force_str
    from socket import error as socket_error

    def call_internal_upload(environ, start_response):
        # Otherwise, just assume it's our internalupload handler
        request = WSGIRequest(environ)

        from djangae.views import internalupload
        response = internalupload(request)

        status = '%s %s' % (response.status_code, response.reason_phrase)
        response_headers = [(str(k), str(v)) for k, v in response.items()]
        start_response(force_str(status), response_headers)
        return response

    def handler(environ, start_response):
        path = environ["PATH_INFO"]

        # If this is an image serving URL, then use use the blob_image WSGI app
        if re.match(blob_image.BLOBIMAGE_URL_PATTERN, path.lstrip("/")):
            return blob_image.Application()(environ, start_response)
        elif re.match(gcs_server.GCS_URL_PATTERN, path.lstrip("/")):
            return gcs_server.Application()(environ, start_response)

        return blob_upload.Application(call_internal_upload)(environ, start_response)

    port = int(os.environ['SERVER_PORT'])
    host = os.environ['SERVER_NAME']
    logging.info("Starting blobstore service on %s:%s", host, port)
    try:
        server = make_server(host, port, handler, handler_class=NoLogRequestHandler)
    except socket_error:
        logging.warning("Not starting blobstore service, it may already be running")
        return

    blobstore_service = threading.Thread(target=server.serve_forever)
    blobstore_service.daemon = True
    blobstore_service.start()


def stop_blobstore_service():
    global blobstore_service
    global server

    if not blobstore_service:
        return

    server.shutdown()
    blobstore_service.join(5)
    blobstore_service = None
