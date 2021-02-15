# STANDARD LIB
import re

# THIRD PARTY
from django.core.exceptions import ImproperlyConfigured
from django.db.models.fields import files


class SaveUrlMixin(object):
    """ Mixin for FieldFile (and ImageFieldFile) class to override `save` to set the file's URL as
        the value of another attribute (field) on the model instance.
    """

    def save(self, *args, **kwargs):
        """ Save the file as normal, but also set the file's URL as the value of the `url_field`
            on the model instance.
        """
        save = kwargs.pop("save", False)  # Same default as FieldFile.save
        kwargs["save"] = False  # Don't save the model instance YET; we want to set the URL first
        super(SaveUrlMixin, self).save(*args, **kwargs)
        # If a url_field has been specified, set the value of the file's URL into that field.
        # Note: the url_field is the attribute name, not the actually field itself.
        if self.field.url_field:
            setattr(self.instance, self.field.url_field, self.url)

        if save:
            self.instance.save()
    save.alters_data = True


class UrlFieldOptionMixin(object):
    """ Mixin to allow the `url_field` option to be passed to FileField and ImageField. """

    def __init__(self, *args, **kwargs):
        self.url_field = kwargs.pop("url_field", None)
        # TODO: Ideally we would check whether the specified field actually exists on the model,
        # but even if we did the check in `contribute_to_class` we can't guarantee whether the
        # other field will have been added to the model yet or not.
        if self.url_field is not None and not is_valid_model_field_name(self.url_field):
            raise ImproperlyConfigured(
                "'url_field' argument must be a string of the name of a field on the model."
            )
        super(UrlFieldOptionMixin, self).__init__(*args, **kwargs)


class FieldFile(SaveUrlMixin, files.FieldFile):
    """ FieldFile which saves its `url` value to a separate field on the model instance when saved.
    """
    pass


class ImageFieldFile(SaveUrlMixin, files.ImageFieldFile):
    """ ImageFieldFile which saves its `url` value to a separate field on the model instance when saved.
    """
    pass


class FileField(UrlFieldOptionMixin, files.FileField):
    """ A FileField which caches the URL in a separate model field.
        This is particularly useful when looking up the URL is a costly operation, e.g. with remote
        storage backends such as Google Cloud Storage.
    """

    attr_class = FieldFile


class ImageField(UrlFieldOptionMixin, files.ImageField):
    """ An ImageField which caches the URL in a separate model field.
        This is particularly useful when looking up the URL is a costly operation, e.g. with remote
        storage backends such as Google Cloud Storage.
    """

    attr_class = ImageFieldFile


def is_valid_model_field_name(value):
    """ Is the given value a string containing a valid model field name? """
    return isinstance(value, (str, unicode)) and re.match(r"[a-zA-Z_][a-zA-Z0-9_]*", value)


