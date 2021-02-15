# THIRD PARTY
from django.core.mail import send_mail
from django.test import override_settings
from google.appengine.api.app_identity import get_application_id
from google.appengine.api.mail_errors import InvalidSenderError

# DJANGAE
from djangae.contrib import sleuth
from djangae.test import TestCase


class EmailBackendTests(TestCase):

    def _get_valid_sender_address(self):
        """ Return an email address which will be allowed as a 'from' address for the current App
            Engine app.
        """
        return "example@%s.appspotmail.com" % get_application_id()

    @override_settings(EMAIL_BACKEND='djangae.mail.EmailBackend')
    def test_send_email(self):
        """ Test that sending an email using Django results in the email being sent through App
            Engine.
        """
        with sleuth.watch('djangae.mail.aeemail.EmailMessage.send') as gae_send:
            send_mail("Subject", "Hello", self._get_valid_sender_address(), ["1@example.com"])
            self.assertTrue(gae_send.called)

    @override_settings(EMAIL_BACKEND='djangae.mail.AsyncEmailBackend')
    def test_send_email_deferred(self):
        """ Test that sending an email using Django results in the email being sent through App
            Engine.
        """
        with sleuth.watch('djangae.mail.aeemail.EmailMessage.send') as gae_send:
            send_mail("Subject", "Hello", self._get_valid_sender_address(), ["1@example.com"])
            self.process_task_queues()
            self.assertTrue(gae_send.called)

    @override_settings(EMAIL_BACKEND='djangae.mail.EmailBackend')
    def test_invalid_sender_address_is_logged(self):
        """ If we use an invalid 'from' address, we want this to be logged. App Engine doesn't
            include the invalid address in its error message, so we have to log it in Djangae.
        """
        invalid_from_address = "larry@google.com"
        with sleuth.watch("djangae.mail.logger.error") as log_err:
            # The SDK doesn't raise InvalidSenderError, so we have to force it to blow up
            with sleuth.detonate("djangae.mail.aeemail.EmailMessage.send", InvalidSenderError):
                try:
                    send_mail("Subject", "Hello", invalid_from_address, ["1@example.com"])
                except InvalidSenderError:
                    pass
            self.assertTrue(log_err.called)
            call_args = log_err.calls[0].args
            # The invalid 'from' address  should be logged somewhere in the args
            args_str = u"".join(unicode(a)for a in call_args)
            self.assertTrue(invalid_from_address in args_str)
