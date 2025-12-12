// Give Food Service Worker for Web Push Notifications
// This file must be served from the root of the website

// Firebase SDKs loaded from Google's CDN as recommended by Firebase documentation.
// SRI hashes are not provided by Firebase for their CDN-hosted SDKs.
importScripts('https://www.gstatic.com/firebasejs/9.22.0/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/9.22.0/firebase-messaging-compat.js');

// Firebase will be initialized when we receive the config from the main page
let messaging = null;

// Listen for messages from the main page to get Firebase config
self.addEventListener('message', function(event) {
    if (event.data && event.data.type === 'FIREBASE_CONFIG') {
        const config = event.data.config;
        if (!firebase.apps.length) {
            firebase.initializeApp(config);
        }
        messaging = firebase.messaging();
        
        // Set up background message handler
        messaging.onBackgroundMessage(function(payload) {
            console.log('[Service Worker] Received background message:', payload);
            
            const notificationTitle = payload.notification?.title || payload.data?.title || 'Give Food';
            const notificationOptions = {
                body: payload.notification?.body || payload.data?.body || '',
                icon: '/static/img/logo.svg',
                badge: '/static/img/logo.svg',
                data: {
                    foodbank_slug: payload.data?.foodbank_slug,
                    click_action: payload.data?.click_action || payload.fcmOptions?.link
                }
            };
            
            return self.registration.showNotification(notificationTitle, notificationOptions);
        });
        
        // Confirm config received
        if (event.ports && event.ports[0]) {
            event.ports[0].postMessage({ success: true });
        }
    }
});

// Handle notification click
self.addEventListener('notificationclick', function(event) {
    event.notification.close();
    
    // Get the URL from the notification data
    let url = '/needs/';
    if (event.notification.data && event.notification.data.foodbank_slug) {
        url = '/needs/at/' + event.notification.data.foodbank_slug + '/';
    }
    if (event.notification.data && event.notification.data.click_action) {
        url = event.notification.data.click_action;
    }

    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function(clientList) {
            // If there's an existing window, focus it
            for (let i = 0; i < clientList.length; i++) {
                const client = clientList[i];
                if ('focus' in client) {
                    return client.focus().then(function(focusedClient) {
                        if ('navigate' in focusedClient) {
                            return focusedClient.navigate(url);
                        }
                    });
                }
            }
            // Otherwise open a new window
            if (clients.openWindow) {
                return clients.openWindow(url);
            }
        })
    );
});

// Fallback: Handle push events directly (for non-Firebase push or when Firebase handler doesn't trigger)
self.addEventListener('push', function(event) {
    // Only handle if messaging hasn't been set up (Firebase will handle its own messages)
    if (messaging) {
        return; // Let Firebase handle it
    }
    
    if (event.data) {
        try {
            const data = event.data.json();
            const notification = data.notification || {};
            const title = notification.title || data.data?.title || 'Give Food';
            const options = {
                body: notification.body || data.data?.body || '',
                icon: '/static/img/logo.svg',
                badge: '/static/img/logo.svg',
                data: data.data || {}
            };
            event.waitUntil(
                self.registration.showNotification(title, options)
            );
        } catch (e) {
            // If not JSON, try to show as text
            const title = 'Give Food';
            const options = {
                body: event.data.text(),
                icon: '/static/img/logo.svg',
                badge: '/static/img/logo.svg'
            };
            event.waitUntil(
                self.registration.showNotification(title, options)
            );
        }
    }
});
