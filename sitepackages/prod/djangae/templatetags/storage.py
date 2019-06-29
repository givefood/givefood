from django import template

register = template.Library()

def blobstore_upload_url(destination_url):
    from google.appengine.ext.blobstore import create_upload_url
    return create_upload_url(unicode(destination_url))

def gcs_upload_url(destination_url, bucket_name):
    from google.appengine.ext.blobstore import create_upload_url
    return create_upload_url(unicode(destination_url), gs_bucket_name=unicode(bucket_name))

register.simple_tag(blobstore_upload_url)
register.simple_tag(gcs_upload_url)
