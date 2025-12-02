"""
Push notification subscription API endpoints
Handles browser push notification subscriptions
"""
import json
import logging
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

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
        
        # Import Firebase Admin SDK for push notifications
        try:
            import firebase_admin
            from firebase_admin import messaging
        except ImportError:
            logger.error('Firebase Admin SDK not available')
            return JsonResponse({
                'success': False,
                'message': 'Push notifications not configured'
            }, status=500)
        
        # Subscribe the token to the topic
        try:
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
