import json
import base64

from django import forms
from django.contrib import admin
from django.db import models
from django.utils import six
from django.utils.safestring import mark_safe
from django.core.urlresolvers import reverse
from django.contrib.admin.templatetags.admin_static import static

# DJANGAE
from djangae.utils import memoized


class TrueOrNullFormField(forms.BooleanField):
    def clean(self, value):
        if value:
            return True
        return None


class ListWidget(forms.TextInput):
    """ A widget for being able to display a ListField and SetField. """

    def render(self, name, value, attrs=None):
        if isinstance(value, (list, tuple, set)):
            value = u', '.join([unicode(v) for v in value])
        return super(ListWidget, self).render(name, value, attrs)

    def value_from_datadict(self, data, files, name):
        """ Given a dictionary of data and this widget's name, returns the value
            of this widget. Returns None if it's not provided.
        """
        value = data.get(name, '')
        if isinstance(value, six.string_types):
            value = value.split(',')
        return [v.strip() for v in value if v.strip()]


class ListFormField(forms.Field):
    """ A form field for being able to display a ListField and SetField. """

    widget = ListWidget
    delimiter = ','

    def clean(self, value):
        if value:
            if isinstance(value, (list, tuple, set)):
                self._check_values_against_delimiter(value)
                return value
            return [v.strip() for v in value.split(',') if v.strip()]
        return []

    def _check_values_against_delimiter(self, values):
        delimiter = self.delimiter  # faster
        for value in values:
            assert delimiter not in value


class JSONWidget(forms.Textarea):
    """ A widget for being able to display a JSONField in a form. """

    def render(self, name, value, attrs=None):
        """ Dump the python object to JSON if it hasn't been done yet. """
        from djangae.fields.json import dumps
        if not isinstance(value, six.string_types):
            value = dumps(value)
        return super(JSONWidget, self).render(name, value, attrs)


class JSONFormField(forms.CharField):
    """ A form field for being able to display a JSONField in a form.
        The JSON is rendered as string in a textarea, but is parsed to python (be)for validation.
     """

    widget = JSONWidget

    def clean(self, value):
        """ (Try to) parse JSON string back to python. """
        if isinstance(value, six.string_types):
            if value == "":
                value = None
            try:
                value = json.loads(value)
            except ValueError:
                raise forms.ValidationError("Could not parse value as JSON")
        return value


#Basic obfuscation, just so that the db_table doesn't
#appear in forms. (Not the end of the world if it does, but it's nice to
# hide these things). We don't encrypt for performance reasons.
#http://en.wikipedia.org/wiki/Vigen%C3%A8re_cipher

_VC_KEY = "1K94KG8L" #Fixed key, don't change this!!

def model_path(obj):
    return obj._meta.db_table

def vc_encode(string):
    enc = []
    for i in range(len(string)):
        key_c = _VC_KEY[i % len(_VC_KEY)]
        enc_c = chr((ord(string[i]) + ord(key_c)) % 256)
        enc.append(enc_c)
    return base64.urlsafe_b64encode("".join(enc))

def vc_decode(enc):
    dec = []
    enc = base64.urlsafe_b64decode(str(enc))
    for i in range(len(enc)):
        key_c = _VC_KEY[i % len(_VC_KEY)]
        dec_c = chr((256 + ord(enc[i]) - ord(key_c)) % 256)
        dec.append(dec_c)
    return "".join(dec)

def encode_pk(pk, obj_cls):
    assert pk is not None

    return vc_encode("{0}|{1}".format(obj_cls._meta.db_table, pk))

def decode_pk(encoded):
    result = vc_decode(encoded)

    model_ref, pk = result.split("|")
    return model_ref, pk


class GenericRelationWidget(forms.MultiWidget):
    def __init__(self, widgets=None, *args, **kwargs):
        widgets = (
            forms.Select(),
            GenericFKInput(),
        )
        super(GenericRelationWidget, self).__init__(widgets=widgets, *args, **kwargs)

    def decompress(self, value):
        if isinstance(value, basestring):
            return decode_pk(value)
        if value:
            return [value._meta.db_table, value.pk]
        return [None, None]


class GenericFKInput(forms.TextInput):
    def __init__(self, *args, **kwargs):
        super(GenericFKInput, self).__init__(*args, **kwargs)

    def render(self, name, value, attrs):
        urls = {}
        for m in admin.site._registry:
            urls[model_path(m)] = reverse('admin:%s_%s_changelist' % (m._meta.app_label, m._meta.module_name))
        urls = json.dumps(urls)
        safe_name = name.replace('-', '_')
        extra = []
        extra.append(u'''<script type="text/javascript">var urls = %s; function popup_%s(trigger) {
            var name = trigger.id.replace(/^lookup_/, '');
            name = id_to_windowname(name);
            var chosen_model = django.jQuery(trigger).siblings('select').val();
            if (chosen_model in urls) {
                var href = urls[chosen_model] + '?pop=1'
                var win = window.open(href, name, 'height=500,width=800,resizable=yes,scrollbars=yes');
                win.focus();
            }
            return false;
            }
        </script>\n''' % (urls, safe_name))
        extra.append(u'<a href="" class="related-lookup" id="lookup_id_%s" onclick="return popup_%s(this);"> ' % (name, safe_name))
        extra.append(u'<img src="%s" width="16" height="16" alt="%s" /></a>' % (static('admin/img/selector-search.gif'), 'Lookup'))
        output = [super(GenericFKInput, self).render(name, value, attrs)] + extra
        return mark_safe(u''.join(output))

@memoized
def model_from_db_table(db_table):
    for app in models.get_apps():
        for model in models.get_models(app):
            if model._meta.db_table == db_table:
                return model
    raise ValueError("Couldn't find model class for %s" % db_table)

_CHOICES = None

@memoized
def get_all_model_choices():
    global _CHOICES
    if _CHOICES is None:
        _CHOICES = [
            ('', 'None')] + [(model_path(m), m.__name__)
            for m in models.get_models()
        ]
    return _CHOICES

class GenericRelationFormfield(forms.MultiValueField):
    def __init__(self, fields=None, widget=None, choices=None, *args, **kwargs):
        fields = (
            forms.ChoiceField(),
            forms.CharField(max_length=30)
        )

        super(GenericRelationFormfield, self).__init__(fields=fields, widget=GenericRelationWidget(), *args, **kwargs)
        self.widget.widgets[0].choices = self.fields[0].choices = choices or get_all_model_choices()

    @classmethod
    def to_python(cls, value, model_ref=None, pk=None):
        if model_ref is None:
            if value is None:
                return None

            if isinstance(value, models.Model):
                return value

            model_ref, pk = decode_pk(value)

        try:
            pk = int(pk)
        except (ValueError, TypeError):
            raise forms.ValidationError('Invalid instance key.')

        model = cls.load_model(model_ref)
        try:
            return model.objects.get(pk=pk)
        except model.DoesNotExist:
            raise forms.ValidationError('Invalid instance key.')

    @classmethod
    def load_model(cls, model_ref):
        return model_from_db_table(model_ref)

    def validate(self, value):
        self.to_python(value)

    @classmethod
    def to_string(cls, value):
        if value is None:
            return None

        if isinstance(value, basestring):
            return value
        return encode_pk(value.pk, value)

    def compress(self, data_list):
        if not data_list or not data_list[0]:
            return None
        return self.to_python(None, *data_list)
