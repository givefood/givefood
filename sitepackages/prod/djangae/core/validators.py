from django.core.validators import BaseValidator
from django.utils.translation import ungettext_lazy


class MaxBytesValidator(BaseValidator):
    compare = lambda self, a, b: a > b
    clean = lambda self, x: len(x.encode('utf-8'))
    message = ungettext_lazy(
        'Ensure this value has at most %(limit_value)d byte (it has %(show_value)d).',
        'Ensure this value has at most %(limit_value)d bytes (it has %(show_value)d).',
        'limit_value')
    code = 'max_length'
