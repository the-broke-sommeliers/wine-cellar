from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _


def send_opened_bottle_reminder(user, items):
    text_content = render_to_string(
        "emails/opened_bottle_reminder.txt",
        context={"items": items, "user": user},
    )

    msg = EmailMultiAlternatives(
        _("Reminder to finish your opened wine(s)"), text_content, to=[user.email]
    )
    msg.send()


def send_drink_by_reminder(user, wines):
    text_content = render_to_string(
        "emails/drink_by_reminder.txt",
        context={"wines": wines, "user": user},
    )

    msg = EmailMultiAlternatives(
        _("Reminder to drink your wine(s)"), text_content, to=[user.email]
    )
    msg.send()
