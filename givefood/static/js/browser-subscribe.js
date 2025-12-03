/**
 * Browser push notification subscription handler
 * Handles subscribing users to food bank notification topics
 */

// Push notification configuration - these values should be set from Django template/settings
const firebaseConfig = window.firebaseConfig || {
    apiKey: "",
    authDomain: "",
    projectId: "",
    storageBucket: "",
    messagingSenderId: "",
    appId: ""
};

// VAPID key for web push - should be set from Django template/settings
const vapidKey = window.firebaseVapidKey || "";

// LocalStorage key for tracking subscriptions
const SUBSCRIPTIONS_KEY = 'gf_push_subscriptions';

/**
 * Get list of subscribed food bank IDs from localStorage
 * @returns {Array} Array of food bank UUIDs user is subscribed to
 */
function getSubscribedFoodbanks() {
    try {
        const subscriptions = localStorage.getItem(SUBSCRIPTIONS_KEY);
        return subscriptions ? JSON.parse(subscriptions) : [];
    } catch (e) {
        console.error('Error reading subscriptions from localStorage:', e);
        return [];
    }
}

/**
 * Add a food bank ID to the subscriptions list
 * @param {string} foodbankId - Food bank UUID
 */
function addSubscription(foodbankId) {
    try {
        const subscriptions = getSubscribedFoodbanks();
        if (!subscriptions.includes(foodbankId)) {
            subscriptions.push(foodbankId);
            localStorage.setItem(SUBSCRIPTIONS_KEY, JSON.stringify(subscriptions));
        }
    } catch (e) {
        console.error('Error saving subscription to localStorage:', e);
    }
}

/**
 * Remove a food bank ID from the subscriptions list
 * @param {string} foodbankId - Food bank UUID
 */
function removeSubscription(foodbankId) {
    try {
        const subscriptions = getSubscribedFoodbanks();
        const filtered = subscriptions.filter(id => id !== foodbankId);
        localStorage.setItem(SUBSCRIPTIONS_KEY, JSON.stringify(filtered));
    } catch (e) {
        console.error('Error removing subscription from localStorage:', e);
    }
}

/**
 * Check if user is subscribed to a specific food bank
 * @param {string} foodbankId - Food bank UUID
 * @returns {boolean} True if subscribed
 */
function isSubscribed(foodbankId) {
    const subscriptions = getSubscribedFoodbanks();
    return subscriptions.includes(foodbankId);
}

/**
 * Initialize push notifications and set up the subscribe button click handler
 */
function initFirebaseSubscribe() {
    const subscribeBtn = document.getElementById('subscribe_browser_btn');
    
    if (!subscribeBtn) {
        return;
    }

    const foodbankId = subscribeBtn.getAttribute('data-foodbankid');
    
    // Check if already subscribed
    if (foodbankId && isSubscribed(foodbankId)) {
        subscribeBtn.textContent = 'Unsubscribe';
        subscribeBtn.classList.add('is-link', 'is-light');
        subscribeBtn.disabled = false;
        subscribeBtn.addEventListener('click', handleUnsubscribeClick);
        return;
    }

    // Check if push notification config is properly set
    if (!firebaseConfig.apiKey || !firebaseConfig.authDomain || !firebaseConfig.projectId || 
        !firebaseConfig.messagingSenderId || !firebaseConfig.appId || !vapidKey) {
        console.warn('Push notification configuration not properly set');
        subscribeBtn.disabled = true;
        subscribeBtn.textContent = 'Browser notifications not configured';
        return;
    }

    // Check if browser supports notifications
    if (!('Notification' in window)) {
        subscribeBtn.disabled = true;
        subscribeBtn.textContent = 'Browser does not support notifications';
        return;
    }

    // Check if service workers are supported
    if (!('serviceWorker' in navigator)) {
        subscribeBtn.disabled = true;
        subscribeBtn.textContent = 'Browser does not support service workers';
        return;
    }

    subscribeBtn.addEventListener('click', handleSubscribeClick);
}

/**
 * Handle the subscribe button click
 */
async function handleSubscribeClick(event) {
    event.preventDefault();
    
    const button = event.target;
    const foodbankId = button.getAttribute('data-foodbankid');
    
    if (!foodbankId) {
        console.error('No foodbank ID found on button');
        showMessage('Error: Missing food bank information', 'error');
        return;
    }

    // Disable button while processing
    button.disabled = true;
    const originalText = button.textContent;
    button.textContent = 'Subscribing...';

    try {
        // Request notification permission
        const permission = await Notification.requestPermission();
        
        if (permission !== 'granted') {
            showMessage('Please allow notifications to subscribe', 'warning');
            button.disabled = false;
            button.textContent = originalText;
            return;
        }

        // Initialize push notification service
        if (!window.firebase || !window.firebase.apps || window.firebase.apps.length === 0) {
            window.firebase.initializeApp(firebaseConfig);
        }

        // Register service worker for push notifications
        let registration;
        try {
            registration = await navigator.serviceWorker.register('/static/push-sw.js');
            await navigator.serviceWorker.ready;
            
            // Send Firebase config to service worker
            if (registration.active) {
                registration.active.postMessage({
                    type: 'FIREBASE_CONFIG',
                    config: firebaseConfig
                });
            }
        } catch (err) {
            console.error('Service worker registration failed:', err);
            showMessage('Failed to register service worker', 'error');
            button.disabled = false;
            button.textContent = originalText;
            return;
        }

        // Get messaging instance for push notifications
        if (!window.firebase.messaging) {
            showMessage('Push notifications not available in this browser', 'error');
            button.disabled = false;
            button.textContent = originalText;
            return;
        }
        
        const messaging = window.firebase.messaging();

        // Get push notification token with service worker registration
        const currentToken = await messaging.getToken({ 
            vapidKey: vapidKey,
            serviceWorkerRegistration: registration
        });
        
        if (!currentToken) {
            showMessage('Failed to get notification token', 'error');
            button.disabled = false;
            button.textContent = originalText;
            return;
        }

        // Subscribe to the topic
        const topic = `foodbank-${foodbankId}`;
        const subscribeResult = await subscribeToTopic(currentToken, topic);
        
        if (subscribeResult.success) {
            // Store subscription in localStorage
            addSubscription(foodbankId);
            
            showMessage('Successfully subscribed to notifications!', 'success');
            button.textContent = 'Unsubscribe';
            button.classList.add('is-link', 'is-light');
            button.disabled = false;
            
            // Remove old event listener and add new one
            button.removeEventListener('click', handleSubscribeClick);
            button.addEventListener('click', handleUnsubscribeClick);
        } else {
            showMessage('Failed to subscribe to notifications', 'error');
            button.disabled = false;
            button.textContent = originalText;
        }
    } catch (error) {
        console.error('Error subscribing to notifications:', error);
        showMessage('Error: ' + error.message, 'error');
        button.disabled = false;
        button.textContent = originalText;
    }
}

/**
 * Handle the unsubscribe button click
 */
async function handleUnsubscribeClick(event) {
    event.preventDefault();
    
    const button = event.target;
    const foodbankId = button.getAttribute('data-foodbankid');
    
    if (!foodbankId) {
        console.error('No foodbank ID found on button');
        showMessage('Error: Missing food bank information', 'error');
        return;
    }

    // Disable button while processing
    button.disabled = true;
    const originalText = button.textContent;
    button.textContent = 'Unsubscribing...';

    try {
        // Initialize push notification service
        if (!window.firebase || !window.firebase.apps || window.firebase.apps.length === 0) {
            window.firebase.initializeApp(firebaseConfig);
        }

        // Get existing service worker registration
        let registration = await navigator.serviceWorker.getRegistration('/static/push-sw.js');
        
        if (!registration) {
            // If no registration exists, try to register it
            try {
                registration = await navigator.serviceWorker.register('/static/push-sw.js');
                await navigator.serviceWorker.ready;
                
                // Send Firebase config to service worker
                if (registration.active) {
                    registration.active.postMessage({
                        type: 'FIREBASE_CONFIG',
                        config: firebaseConfig
                    });
                }
            } catch (err) {
                console.error('Service worker registration failed:', err);
                showMessage('Failed to access service worker', 'error');
                button.disabled = false;
                button.textContent = originalText;
                return;
            }
        }

        // Get messaging instance for push notifications
        if (!window.firebase.messaging) {
            showMessage('Push notifications not available in this browser', 'error');
            button.disabled = false;
            button.textContent = originalText;
            return;
        }
        
        const messaging = window.firebase.messaging();

        // Get push notification token with service worker registration
        const currentToken = await messaging.getToken({ 
            vapidKey: vapidKey,
            serviceWorkerRegistration: registration
        });
        
        if (!currentToken) {
            showMessage('Failed to get notification token', 'error');
            button.disabled = false;
            button.textContent = originalText;
            return;
        }

        // Unsubscribe from the topic
        const topic = `foodbank-${foodbankId}`;
        const unsubscribeResult = await unsubscribeFromTopic(currentToken, topic);
        
        if (unsubscribeResult.success) {
            // Remove subscription from localStorage
            removeSubscription(foodbankId);
            
            showMessage('Successfully unsubscribed from notifications', 'success');
            button.textContent = 'Subscribe to browser notifications';
            button.classList.add('is-link', 'is-light');
            button.disabled = false;
            
            // Remove old event listener and add new one
            button.removeEventListener('click', handleUnsubscribeClick);
            button.addEventListener('click', handleSubscribeClick);
        } else {
            showMessage('Failed to unsubscribe from notifications', 'error');
            button.disabled = false;
            button.textContent = originalText;
        }
    } catch (error) {
        console.error('Error unsubscribing from notifications:', error);
        showMessage('Error: ' + error.message, 'error');
        button.disabled = false;
        button.textContent = originalText;
    }
}

/**
 * Subscribe a token to a food bank notification topic
 * @param {string} token - Push notification token
 * @param {string} topic - Topic name (e.g., "foodbank-uuid")
 * @returns {Promise<{success: boolean, message: string}>}
 */
async function subscribeToTopic(token, topic) {
    try {
        // Call our backend endpoint to subscribe the token to the topic
        // The backend uses push notification services to handle the subscription
        const response = await fetch('/needs/browser/subscribe/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken(),
            },
            body: JSON.stringify({
                token: token,
                topic: topic
            })
        });

        if (!response.ok) {
            throw new Error('Server error: ' + response.status);
        }

        const data = await response.json();
        return { success: true, message: data.message };
    } catch (error) {
        console.error('Error subscribing to topic:', error);
        return { success: false, message: error.message };
    }
}

/**
 * Unsubscribe a token from a food bank notification topic
 * @param {string} token - Push notification token
 * @param {string} topic - Topic name (e.g., "foodbank-uuid")
 * @returns {Promise<{success: boolean, message: string}>}
 */
async function unsubscribeFromTopic(token, topic) {
    try {
        // Call our backend endpoint to unsubscribe the token from the topic
        const response = await fetch('/needs/browser/unsubscribe/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken(),
            },
            body: JSON.stringify({
                token: token,
                topic: topic
            })
        });

        if (!response.ok) {
            throw new Error('Server error: ' + response.status);
        }

        const data = await response.json();
        return { success: true, message: data.message };
    } catch (error) {
        console.error('Error unsubscribing from topic:', error);
        return { success: false, message: error.message };
    }
}

/**
 * Get CSRF token from cookie
 * @returns {string} CSRF token
 */
function getCsrfToken() {
    const name = 'csrftoken';
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

/**
 * Show a message to the user
 * @param {string} message - Message to display
 * @param {string} type - Message type ('success', 'error', 'warning')
 */
function showMessage(message, type) {
    // Create a notification element
    const notification = document.createElement('div');
    notification.className = `notification is-${type}`;
    notification.style.cssText = 'position: fixed; top: 20px; right: 20px; z-index: 1000; max-width: 300px;';
    
    const deleteBtn = document.createElement('button');
    deleteBtn.className = 'delete';
    deleteBtn.onclick = () => notification.remove();
    
    notification.appendChild(deleteBtn);
    notification.appendChild(document.createTextNode(message));
    
    document.body.appendChild(notification);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 5000);
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initFirebaseSubscribe);
} else {
    initFirebaseSubscribe();
}
