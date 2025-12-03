"""
Push notification subscription API endpoints
Handles browser push notification subscriptions
"""
import json
import logging
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from givefood.func import initialize_firebase_admin

logger = logging.getLogger(__name__)


@require_http_methods(["POST"])
def subscribe_to_topic(request):
    """
    Subscribe a browser push notification token to a food bank topic.
    
    Expected POST body:
    {
        "token": "fcm_token_string",
        "topic": "foodbank-uuid"
    }
    """
    try:
        data = json.loads(request.body)
        token = data.get('token')
        topic = data.get('topic')
        
        if not token or not topic:
            return JsonResponse({
                'success': False,
                'message': 'Missing token or topic'
            }, status=400)
        
        # Validate topic format (should be foodbank-{uuid})
        if not topic.startswith('foodbank-'):
            return JsonResponse({
                'success': False,
                'message': 'Invalid topic format'
            }, status=400)
        
        # Initialize Firebase Admin SDK
        if not initialize_firebase_admin():
            logger.error('Failed to initialize Firebase Admin SDK')
            return JsonResponse({
                'success': False,
                'message': 'Push notifications not configured'
            }, status=500)
        
        # Subscribe the token to the topic
        try:
            # Import here to avoid import errors if firebase-admin is not installed
            from firebase_admin import messaging
            
            # Use Firebase Admin SDK to subscribe tokens to a topic
            response = messaging.subscribe_to_topic([token], topic)
            
            if response.success_count > 0:
                logger.info(f'Successfully subscribed token to topic {topic}')
                return JsonResponse({
                    'success': True,
                    'message': 'Successfully subscribed to notifications'
                })
            else:
                logger.warning(f'Failed to subscribe token to topic {topic}: {response.errors}')
                return JsonResponse({
                    'success': False,
                    'message': 'Subscription failed'
                }, status=500)
                
        except Exception as e:
            logger.error(f'Error subscribing to topic: {e}')
            return JsonResponse({
                'success': False,
                'message': 'Server error during subscription'
            }, status=500)
    
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON'
        }, status=400)
    except Exception as e:
        logger.error(f'Unexpected error in subscribe_to_topic: {e}')
        return JsonResponse({
            'success': False,
            'message': 'Server error'
        }, status=500)


@require_http_methods(["POST"])
def unsubscribe_from_topic(request):
    """
    Unsubscribe a browser push notification token from a food bank topic.
    
    Expected POST body:
    {
        "token": "fcm_token_string",
        "topic": "foodbank-uuid"
    }
    """
    try:
        data = json.loads(request.body)
        token = data.get('token')
        topic = data.get('topic')
        
        if not token or not topic:
            return JsonResponse({
                'success': False,
                'message': 'Missing token or topic'
            }, status=400)
        
        # Validate topic format (should be foodbank-{uuid})
        if not topic.startswith('foodbank-'):
            return JsonResponse({
                'success': False,
                'message': 'Invalid topic format'
            }, status=400)
        
        # Initialize Firebase Admin SDK
        if not initialize_firebase_admin():
            logger.error('Failed to initialize Firebase Admin SDK')
            return JsonResponse({
                'success': False,
                'message': 'Push notifications not configured'
            }, status=500)
        
        # Unsubscribe the token from the topic
        try:
            # Import here to avoid import errors if firebase-admin is not installed
            from firebase_admin import messaging
            
            # Use Firebase Admin SDK to unsubscribe tokens from a topic
            response = messaging.unsubscribe_from_topic([token], topic)
            
            if response.success_count > 0:
                logger.info(f'Successfully unsubscribed token from topic {topic}')
                return JsonResponse({
                    'success': True,
                    'message': 'Successfully unsubscribed from notifications'
                })
            else:
                logger.warning(f'Failed to unsubscribe token from topic {topic}: {response.errors}')
                return JsonResponse({
                    'success': False,
                    'message': 'Unsubscription failed'
                }, status=500)
                
        except Exception as e:
            logger.error(f'Error unsubscribing from topic: {e}')
            return JsonResponse({
                'success': False,
                'message': 'Server error during unsubscription'
            }, status=500)
    
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON'
        }, status=400)
    except Exception as e:
        logger.error(f'Unexpected error in unsubscribe_from_topic: {e}')
        return JsonResponse({
            'success': False,
            'message': 'Server error'
        }, status=500)
