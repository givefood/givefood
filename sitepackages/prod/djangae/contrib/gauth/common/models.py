# THIRD PARTY
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import (
    AbstractBaseUser,
    python_2_unicode_compatible,
    UserManager,
)
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.utils.http import urlquote
from django.db import models
from django.utils import timezone, six
from django.utils.translation import ugettext_lazy as _

# DJANGAE
from djangae.fields import CharOrNoneField, ComputedCharField
from .validators import validate_google_user_id


class GaeUserManager(UserManager):

    def pre_create_google_user(self, email, **extra_fields):
        """ Pre-create a User object for a user who will later log in via Google Accounts. """
        values = dict(
            # defaults which can be overridden
            is_active=True,
        )
        values.update(**extra_fields)
        values.update(
            # things which cannot be overridden
            email=self.normalize_email(email),  # lowercase the domain only
            username=None,
            password=make_password(None),  # unusable password
            # Stupidly, last_login is not nullable, so we can't set it to None.
        )
        return self.create(**values)


def _get_email_lower(user):
    """ Computer function for the computed lowercase email field. """
    # Note that the `email` field is not nullable, but the `email_lower` one is nullable and must
    # not contain empty strings because it is unique
    return user.email and user.email.lower() or None


@python_2_unicode_compatible
class GaeAbstractBaseUser(AbstractBaseUser):
    """ Absract base class for creating a User model which works with the App
    Engine users API. """

    username = CharOrNoneField(
        # This stores the Google user_id, or custom username for non-Google-based users.
        # We allow it to be null so that Google-based users can be pre-created before they log in.
        _('User ID'), max_length=21, unique=True, blank=True, null=True, default=None,
        validators=[validate_google_user_id]
    )
    first_name = models.CharField(_('first name'), max_length=30, blank=True)
    last_name = models.CharField(_('last name'), max_length=30, blank=True)

    # Email addresses are case sensitive, but many email systems and many people treat them as if
    # they're not.  We must store the case-preserved email address to ensure that sending emails
    # always works, but we must be able to query for them case insensitively and therefore we must
    # enforce uniqueness on a case insensitive basis, hence these 2 fields
    email = models.EmailField(_('email address'))
    # The null-able-ness of the email_lower is only to deal with when an email address moves between
    # Google Accounts and therefore we need to wipe it without breaking the unique constraint.
    email_lower = ComputedCharField(
        _get_email_lower, max_length=email.max_length, unique=True, null=True
    )

    is_staff = models.BooleanField(
        _('staff status'), default=False,
        help_text=_('Designates whether the user can log into this admin site.')
    )
    is_active = models.BooleanField(
        _('active'), default=True,
        help_text=_(
            'Designates whether this user should be treated as '
            'active. Unselect this instead of deleting accounts.'
        )
    )
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    objects = GaeUserManager()

    class Meta:
        abstract = True

    def get_absolute_url(self):
        return "/users/%s/" % urlquote(self.username)

    def get_full_name(self):
        """
        Returns the first_name plus the last_name, with a space in between.
        """
        full_name = '%s %s' % (self.first_name, self.last_name)
        return full_name.strip()

    def get_short_name(self):
        "Returns the short name for the user."
        return self.first_name

    def email_user(self, subject, message, from_email=None):
        """
        Sends an email to this User.
        """
        send_mail(subject, message, from_email, [self.email])

    def __str__(self):
        """
            We have to override this as username is nullable. We either return the email
            address, or if there is a username, we return "email (username)".
        """
        username = self.get_username()
        if username:
            return "{} ({})".format(six.text_type(self.email), six.text_type(username))
        return six.text_type(self.email)

    def validate_unique(self, exclude=None):
        """ Check that the email address does not already exist by querying on email_lower. """
        exclude = exclude or []
        if "email_lower" not in exclude:
            # We do our own check using the email_lower field, so we don't need Django to query
            # on it as well
            exclude.append("email_lower")

        try:
            super(GaeAbstractBaseUser, self).validate_unique(exclude=exclude)
        except ValidationError as super_error:
            pass
        else:
            super_error = None

        if self.email and "email" not in exclude:
            existing = self.__class__.objects.filter(email_lower=self.email.lower())
            if not self._state.adding:
                existing = existing.exclude(pk=self.pk)
            if existing.exists():
                model_name = self._meta.verbose_name
                field_name = self._meta.get_field("email").verbose_name
                message = "%s with this %s already exists" % (model_name, field_name)
                error_dict = {"email": [message]}
                if super_error:
                    super_error.update_error_dict(error_dict)
                    raise super_error
                else:
                    raise ValidationError(error_dict)
        elif super_error:
            raise
