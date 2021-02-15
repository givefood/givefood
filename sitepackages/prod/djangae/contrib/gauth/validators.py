# STANDARD LIB
import re

# THIRD PARTY
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _


def validate_google_user_id(value):
    """ Validates that the given value is either empty, None, or 21 digits. """
    if value and not re.match(r'^\d{21}$', value):
        raise ValidationError(_('Google user ID should be 21 digits.'))
