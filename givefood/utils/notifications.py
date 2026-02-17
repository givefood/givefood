#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import logging
import random

import requests
from django.urls import reverse
from django.template.loader import render_to_string
from django.utils import timezone
from django.contrib.humanize.templatetags.humanize import apnumber
from django_tasks import task

from givefood.const.general import SITE_DOMAIN
from givefood.utils.cache import get_cred


# WhatsApp Integration Constants
WHATSAPP_PHONE_NUMBER_ID = "890504590819478"
WHATSAPP_FROM_NUMBER = "+442039206758"


def post_to_subscriber(need, subscriber):

    possible_emoji = [
        "🍝",
        "🍲",
        "🍛",
        "🥫",
        "🌽",
        "🥕",
        "🥔",
        "🍚",
        "🍽️",
        "🍴",
        "🥘",
        "🍅",
        "🫘",
        "🫛",
        "🥄",
        "🥣",
        "🥧",
    ]
    emoji = random.choice(possible_emoji)

    subject = "%s %s needs %s items" % (emoji, need.foodbank.full_name(), apnumber(need.no_items()))

    text_body = render_to_string(
        "wfbn/emails/notification.txt",
        {
            "need":need,
            "subscriber":subscriber,
        }
    )
    html_body = render_to_string(
        "wfbn/emails/notification.html",
        {
            "need":need,
            "subscriber":subscriber,
        }
    )

    # Generate one-click unsubscribe URL (RFC 8058)
    unsubscribe_url = "%s%s?key=%s" % (
        SITE_DOMAIN,
        reverse("wfbn:updates", kwargs={"slug": need.foodbank.slug, "action": "unsubscribe"}),
        subscriber.unsub_key
    )

    send_email_async.enqueue(
        to = subscriber.email,
        subject = subject,
        body = text_body,
        html_body = html_body,
        is_broadcast = True,
        unsubscribe_url = unsubscribe_url,
    )


@task(queue_name="email")
def send_email_async(to, subject, body, html_body=None, cc=None, cc_name=None, reply_to=None, reply_to_name=None, is_broadcast=False, bcc=None, bcc_name=None, unsubscribe_url=None):
    return send_email(
        to = to,
        subject = subject,
        body = body,
        html_body = html_body,
        cc = cc,
        cc_name = cc_name,
        reply_to = reply_to,
        reply_to_name = reply_to_name,
        is_broadcast = is_broadcast,
        bcc = bcc,
        bcc_name = bcc_name,
        unsubscribe_url = unsubscribe_url,
    )


def send_email(to, subject, body, html_body=None, cc=None, cc_name=None, reply_to=None, reply_to_name=None, is_broadcast=False, bcc=None, bcc_name=None, unsubscribe_url=None):

    api_url = "https://api.postmarkapp.com/email"
    server_token = get_cred("postmark_server_token")

    request_headers = {
        "X-Postmark-Server-Token": server_token,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    if is_broadcast:
        message_stream = "broadcast"
    else:
        message_stream = "outbound"

    # Handle test emails
    if reply_to == "test@example.com":
        to = "mail+testemail@givefood.org.uk"

    request_body = {
        "From": "mail@givefood.org.uk",
        "To": to,
        "Cc": cc,
        "Bcc": bcc,
        "Subject": subject,
        "TextBody": body,
        "HtmlBody": html_body,
        "ReplyTo": reply_to,
        "MessageStream": message_stream
      }

    # Add List-Unsubscribe headers for one-click unsubscribe (RFC 8058)
    if unsubscribe_url:
        request_body["Headers"] = [
            {"Name": "List-Unsubscribe", "Value": "<%s>" % unsubscribe_url},
            {"Name": "List-Unsubscribe-Post", "Value": "List-Unsubscribe=One-Click"},
        ]

    result = requests.post(
        api_url,
        headers = request_headers,
        json = request_body,
    )

    if result.status_code == 200:
        return True
    else:
        logging.error(f"Failed to send email to {to}: {result.status_code} - {result.text}")
        return False


def initialize_firebase_admin():
    """
    Initialize Firebase Admin SDK if not already initialized.
    
    Returns:
        bool: True if Firebase is initialized successfully, False otherwise
    """
    import firebase_admin
    from firebase_admin import credentials
    
    # Check if Firebase app is already initialized
    try:
        firebase_admin.get_app()
        return True
    except ValueError:
        # App not initialized, need to initialize it
        cred_string = get_cred("firebase_service_account")
        if not cred_string:
            logging.warning("Firebase service account credentials not found")
            return False
        
        # Parse the JSON string to a dict
        try:
            cred_dict = json.loads(cred_string)
        except json.JSONDecodeError:
            logging.error("Failed to parse firebase_service_account as JSON")
            return False
        
        try:
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            return True
        except Exception as e:
            logging.error(f"Failed to initialize Firebase Admin SDK: {e}")
            return False


def send_firebase_notification(need):
    """
    Send a Firebase Cloud Messaging notification to a food bank's topic.
    
    Args:
        need: FoodbankChange instance with foodbank and need information
    """
    from firebase_admin import messaging
    
    # Initialize Firebase app if not already initialized
    if not initialize_firebase_admin():
        return
    
    # Build the topic name
    topic = f"foodbank-{need.foodbank.uuid}"
    
    # Build the notification title
    title = f"{need.foodbank.name} needs {need.no_items()} items"
    
    # Get all items from the need
    items = need.change_list()
    
    # Firebase has a 4KB limit for the notification payload
    # We need to fit as many items as possible within this limit
    # The limit applies to the entire message, but we'll be conservative
    # and ensure the body stays well under 4KB (4096 bytes)
    max_body_bytes = 4000  # Leave some room for overhead
    
    # Build the body by adding items one by one until we hit the limit
    body_items = []
    current_body = ""
    
    for item in items:
        # Try adding this item
        if body_items:
            test_body = ", ".join(body_items + [item])
        else:
            test_body = item
        
        # Check if adding this item would exceed the limit
        if len(test_body.encode('utf-8')) <= max_body_bytes:
            body_items.append(item)
            current_body = test_body
        else:
            # Can't fit any more items
            break
    
    # Use the body with as many items as fit
    items_text = current_body
    foodbank_url = f"{SITE_DOMAIN}{reverse('wfbn:foodbank', kwargs={'slug': need.foodbank.slug})}"
    
    message = messaging.Message(
        notification=messaging.Notification(
            title=title,
            body=items_text,
        ),
        data={
            "foodbank_slug": need.foodbank.slug,
        },
        webpush=messaging.WebpushConfig(
            notification=messaging.WebpushNotification(
                title=title,
                body=items_text,
                icon="/static/img/notificationicon.svg",
                badge="/static/img/notificationicon.svg",
            ),
            fcm_options=messaging.WebpushFCMOptions(
                link=foodbank_url
            ),
            data={
                "foodbank_slug": need.foodbank.slug,
                "click_action": foodbank_url,
            },
        ),
        topic=topic,
    )
    
    # Send the message
    try:
        response = messaging.send(message)
        logging.info(f"Successfully sent Firebase notification for need {need.need_id} to topic {topic}: {response}")
        return response
    except Exception as e:
        logging.error(f"Failed to send Firebase notification for need {need.need_id}: {e}")
        return None


@task(priority=10)
def send_firebase_notification_async(need_id_str):
    from givefood.models import FoodbankChange
    need = FoodbankChange.objects.get(need_id_str=need_id_str)
    send_firebase_notification(need)
    return True


def _get_vapid_credentials():
    """
    Get VAPID credentials from database.
    
    Returns:
        tuple: (vapid_private_key, vapid_admin_email) or (None, None) if not found
    """
    vapid_public_key = get_cred("VAPID_PUBLIC_KEY")
    vapid_private_key = get_cred("VAPID_PRIVATE_KEY")
    vapid_admin_email = get_cred("VAPID_ADMIN_EMAIL")
    
    if not vapid_public_key or not vapid_private_key or not vapid_admin_email:
        return None, None
    
    return vapid_private_key, vapid_admin_email


def _build_webpush_payload(need):
    """
    Build the web push notification payload for a food bank need.
    
    Args:
        need: FoodbankChange instance with foodbank and need information
        
    Returns:
        dict: Notification payload with head, body, icon, url, and tag
    """
    # Build the notification title
    title = f"{need.foodbank.name} needs {need.no_items()} items"
    
    # Get items for the body
    items = need.change_list()
    
    # Build body with items, staying under reasonable size
    max_body_chars = 200
    body_items = []
    current_body = ""
    
    for item in items:
        if body_items:
            test_body = ", ".join(body_items + [item])
        else:
            test_body = item
        
        if len(test_body) <= max_body_chars:
            body_items.append(item)
            current_body = test_body
        else:
            break
    
    foodbank_url = f"{SITE_DOMAIN}{reverse('wfbn:foodbank', kwargs={'slug': need.foodbank.slug})}"
    
    return {
        "head": title,
        "body": current_body,
        "icon": "/static/img/notificationicon.svg",
        "url": foodbank_url,
        "tag": f"need-{need.need_id}",
    }


def _send_single_push(subscription, payload, vapid_private_key, vapid_admin_email):
    """
    Send a single web push notification.
    
    Args:
        subscription: WebPushSubscription instance
        payload: dict with notification payload
        vapid_private_key: VAPID private key
        vapid_admin_email: VAPID admin email
        
    Returns:
        tuple: (success: bool, should_delete: bool) - whether send succeeded and whether subscription should be deleted
    """
    from pywebpush import webpush, WebPushException
    
    subscription_info = {
        "endpoint": subscription.endpoint,
        "keys": {
            "p256dh": subscription.p256dh,
            "auth": subscription.auth,
        }
    }
    
    try:
        webpush(
            subscription_info=subscription_info,
            data=json.dumps(payload),
            vapid_private_key=vapid_private_key,
            vapid_claims={"sub": f"mailto:{vapid_admin_email}"}
        )
        return True, False
    except WebPushException as e:
        logging.error(f"Failed to send web push to subscription {subscription.id}: {e}")
        # If subscription is invalid (410 Gone or 404), mark for deletion
        if e.response and e.response.status_code in [404, 410]:
            return False, True
        return False, False
    except Exception as e:
        logging.error(f"Unexpected error sending web push to subscription {subscription.id}: {e}")
        return False, False


def send_webpush_notification(need):
    """
    Send web push notifications to subscribers of a food bank using django-webpush.
    
    This uses VAPID (Voluntary Application Server Identification) for web push,
    which is the standard for browser push notifications without Firebase.
    
    Args:
        need: FoodbankChange instance with foodbank and need information
    """
    from givefood.models import WebPushSubscription
    
    vapid_private_key, vapid_admin_email = _get_vapid_credentials()
    if not vapid_private_key:
        logging.warning("VAPID credentials not found, skipping web push notifications")
        return None
    
    # Get all web push subscriptions for this food bank
    subscriptions = WebPushSubscription.objects.filter(foodbank=need.foodbank)
    
    if not subscriptions.exists():
        logging.info(f"No web push subscriptions for food bank {need.foodbank.name}")
        return None
    
    payload = _build_webpush_payload(need)
    
    sent_count = 0
    failed_subscriptions = []
    
    for subscription in subscriptions:
        success, should_delete = _send_single_push(subscription, payload, vapid_private_key, vapid_admin_email)
        if success:
            sent_count += 1
            logging.info(f"Sent web push to subscription {subscription.id}")
        if should_delete:
            failed_subscriptions.append(subscription.id)
    
    # Clean up invalid subscriptions
    if failed_subscriptions:
        WebPushSubscription.objects.filter(id__in=failed_subscriptions).delete()
        logging.info(f"Deleted {len(failed_subscriptions)} invalid web push subscriptions")
    
    logging.info(f"Sent {sent_count} web push notifications for need {need.need_id}")
    return sent_count


@task(priority=10)
def send_webpush_notification_async(need_id_str):
    from givefood.models import FoodbankChange
    need = FoodbankChange.objects.get(need_id_str=need_id_str)
    send_webpush_notification(need)
    return True


def send_single_webpush_notification(subscription, need):
    """
    Send a web push notification to a single subscriber using their subscription details.
    
    Args:
        subscription: WebPushSubscription instance
        need: FoodbankChange instance with foodbank and need information
    
    Returns:
        True if sent successfully, False otherwise
    """
    from givefood.models import WebPushSubscription
    
    vapid_private_key, vapid_admin_email = _get_vapid_credentials()
    if not vapid_private_key:
        logging.warning("VAPID credentials not found, cannot send web push notification")
        return False
    
    payload = _build_webpush_payload(need)
    
    success, should_delete = _send_single_push(subscription, payload, vapid_private_key, vapid_admin_email)
    
    if success:
        logging.info(f"Sent test web push to subscription {subscription.id}")
    
    if should_delete:
        WebPushSubscription.objects.filter(id=subscription.id).delete()
        logging.info(f"Deleted invalid web push subscription {subscription.id}")
    
    return success


def send_whatsapp_message(to_phone, message):
    """
    Send a plain text WhatsApp message.
    
    Args:
        to_phone: Phone number in international format (e.g., +447123456789)
        message: Text message to send
        
    Returns:
        True if sent successfully, False otherwise
    """
    access_token = get_cred("whatsapp_accesstoken")
    if not access_token:
        logging.warning("WhatsApp access token not found")
        return False
    
    url = f"https://graph.facebook.com/v24.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    
    # Normalize phone number - remove leading + for WhatsApp API
    phone_normalized = to_phone.lstrip('+')
    
    payload = {
        "messaging_product": "whatsapp",
        "to": phone_normalized,
        "type": "text",
        "text": {
            "body": message
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            logging.info(f"Successfully sent WhatsApp message to {to_phone}")
            return True
        else:
            logging.error(f"Failed to send WhatsApp message: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logging.error(f"Error sending WhatsApp message: {e}")
        return False


def send_whatsapp_template_notification(subscription, need):
    """
    Send a WhatsApp template notification for a food bank need.
    Uses the 'foodbankneed' template.
    
    Args:
        subscription: WhatsappSubscriber instance
        need: FoodbankChange instance with foodbank and need information
        
    Returns:
        True if sent successfully, False otherwise
    """
    access_token = get_cred("whatsapp_accesstoken")
    if not access_token:
        logging.warning("WhatsApp access token not found")
        return False
    
    url = f"https://graph.facebook.com/v24.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    
    # Get food bank name and items for template
    foodbank_name = need.foodbank.name
    items = need.change_list()
    
    # Get 3 items for the template
    item1 = items[0] if len(items) > 0 else ""
    item2 = items[1] if len(items) > 1 else ""
    item3 = items[2] if len(items) > 2 else ""
    
    # Normalize phone number - remove leading + for WhatsApp API
    phone_normalized = subscription.phone_number.lstrip('+')
    
    payload = {
        "messaging_product": "whatsapp",
        "to": phone_normalized,
        "type": "template",
        "template": {
            "name": "foodbankneed2",
            "language": {
                "code": "en"
            },
            "components": [
                {
                    "type": "header",
                    "parameters": [
                        {
                            "type": "text",
                            "text": foodbank_name
                        }
                    ]
                },
                {
                    "type": "body",
                    "parameters": [
                        {
                            "type": "text",
                            "text": foodbank_name
                        },
                        {
                            "type": "text",
                            "text": item1
                        },
                        {
                            "type": "text",
                            "text": item2
                        },
                        {
                            "type": "text",
                            "text": item3
                        }
                    ]
                },
                {
                    "type": "button",
                    "sub_type": "url",
                    "index": "0",
                    "parameters": [
                        {
                            "type": "text",
                            "text": need.foodbank.slug
                        }
                    ]
                }
            ]
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            logging.info(f"Successfully sent WhatsApp notification to {subscription.phone_number} for {foodbank_name}")
            return True
        else:
            logging.error(f"Failed to send WhatsApp notification: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logging.error(f"Error sending WhatsApp notification: {e}")
        return False


def send_whatsapp_notification(need):
    """
    Send WhatsApp notifications to all subscribers of a food bank.
    
    Args:
        need: FoodbankChange instance with foodbank and need information
        
    Returns:
        Number of notifications sent successfully
    """
    from givefood.models import WhatsappSubscriber
    
    # Get all WhatsApp subscriptions for this food bank
    subscriptions = WhatsappSubscriber.objects.filter(foodbank=need.foodbank)
    
    if not subscriptions.exists():
        logging.info(f"No WhatsApp subscriptions for food bank {need.foodbank.name}")
        return 0
    
    sent_count = 0
    
    for subscription in subscriptions:
        success = send_whatsapp_template_notification(subscription, need)
        if success:
            sent_count += 1
            # Update last_notified timestamp
            subscription.last_notified = timezone.now()
            subscription.save()
    
    logging.info(f"Sent {sent_count} WhatsApp notifications for need {need.need_id}")
    return sent_count


@task(priority=10)
def send_whatsapp_notification_async(need_id_str):
    from givefood.models import FoodbankChange
    need = FoodbankChange.objects.get(need_id_str=need_id_str)
    send_whatsapp_notification(need)
