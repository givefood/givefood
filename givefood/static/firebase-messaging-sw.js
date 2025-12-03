/**
 * Push Notification Service Worker
 * Handles background push notifications for food bank updates
 */

// Import scripts for push messaging
importScripts('https://www.gstatic.com/firebasejs/9.22.0/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/9.22.0/firebase-messaging-compat.js');

// Initialize Firebase with a minimal config on service worker activation
// The full config will be sent from the main thread
self.addEventListener('activate', (event) => {
    console.log('Service worker activated');
});

// Listen for configuration from main thread
self.addEventListener('message', (event) => {
    if (event.data && event.data.type === 'FIREBASE_CONFIG') {
        const firebaseConfig = event.data.config;
        
        // Initialize push notification service with received config
        if (firebaseConfig) {
            try {
                // Check if Firebase is already initialized
                if (!firebase.apps?.length) {
                    firebase.initializeApp(firebaseConfig);
                    console.log('Firebase initialized in service worker');
                    
                    // Get messaging instance and set up message handler
                    const messaging = firebase.messaging();
                    
                    // Handle background messages
                    messaging.onBackgroundMessage((payload) => {
                        console.log('Received background message:', payload);
                        
                        const notificationTitle = payload.notification?.title || 'Food Bank Update';
                        const notificationOptions = {
                            body: payload.notification?.body || 'New items needed',
                            icon: '/static/img/logo.svg',
                            badge: '/static/img/logo.svg',
                            data: payload.data,
                        };
                        
                        return self.registration.showNotification(notificationTitle, notificationOptions);
                    });
                }
            } catch (error) {
                console.error('Error initializing Firebase in service worker:', error);
            }
        }
    }
});

// Handle notification click
self.addEventListener('notificationclick', (event) => {
    event.notification.close();
    
    // Get the food bank slug from notification data
    const foodbankSlug = event.notification.data?.foodbank_slug;
    
    if (foodbankSlug) {
        // Use relative URL to work in all environments
        const url = `/needs/at/${foodbankSlug}/`;
        
        event.waitUntil(
            clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
                // Check if there's already a window open with this URL
                for (const client of clientList) {
                    if (client.url.includes(url) && 'focus' in client) {
                        return client.focus();
                    }
                }
                // If not, open a new window
                if (clients.openWindow) {
                    return clients.openWindow(url);
                }
            })
        );
    }
});
