import logging
from django.core.mail import EmailMultiAlternatives
from django.template import loader, Template, Context
from django.utils.html import strip_tags

logger = logging.getLogger('log')


def _render(template, context):
    if isinstance(context, dict):
        context = Context(context)
    if isinstance(template, basestring):
        template = Template(template)
    return template.render(context)


class TemplateEmailBase(object):
    subject = ''
    html_template = 'wl/emails/base_email.html'
    # txt_template can be None, in this case a 'tag-stripped' version of the html will be sent. (see send)
    txt_template = 'wl/emails/base-email.txt'

    def send_to_user(self, user, context=None):
        return self.send(user.email, context=context)

    def send(self, to_addresses, from_address=None, context=None, attachments=None):
        """
        Send an email using EmailMultiAlternatives with text and html.
        :param to_addresses: a string or a list of addresses
        :param from_address: if None the settings.DEFAULT_FROM_EMAIL is used
        :param context: a dictionary or a Context object used for rendering the templates.
        :param attachments: a list of (filepath, content, mimetype) triples
               (see https://docs.djangoproject.com/en/1.9/topics/email/)
        :return:
        """
        # The next line will throw a TemplateDoesNotExist if html template cannot be found
        html_template = loader.get_template(self.html_template)
        # render html
        html_body = _render(html_template, context)
        if self.txt_template is not None:
            txt_template = loader.get_template(self.txt_template)
            txt_body = _render(txt_template, context)
        else:
            txt_body = strip_tags(html_body)

        # build message
        if isinstance(to_addresses, basestring):
            to_addresses = [to_addresses]
        if attachments is not None and not isinstance(attachments, list):
                attachments = list(attachments)
        msg = EmailMultiAlternatives(self.subject, txt_body, from_email=from_address, to=to_addresses,
                                     attachments=attachments)
        msg.attach_alternative(html_body, 'text/html')
        try:
            msg.send(fail_silently=False)
            return msg
        except Exception as e:
            logger.exception("Error while sending email to {}: {}".format(to_addresses, e))
            return None
