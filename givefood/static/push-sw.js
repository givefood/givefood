/**
 * Push Notification Service Worker
 * Handles background push notifications for food bank updates
 */

// Import scripts for push messaging
importScripts('https://www.gstatic.com/firebasejs/9.22.0/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/9.22.0/firebase-messaging-compat.js');

// Firebase configuration will be injected here by the server
// FIREBASE_CONFIG_PLACEHOLDER

// Initialize Firebase immediately when the service worker loads
// This ensures we can receive background messages even when no page is open
if (typeof firebaseConfig !== 'undefined' && firebaseConfig &&
    firebaseConfig.apiKey && firebaseConfig.projectId &&
    firebaseConfig.messagingSenderId && firebaseConfig.appId) {
    try {
        // Initialize Firebase app
        firebase.initializeApp(firebaseConfig);
        console.log('Firebase initialized in service worker on load');
        
        // Get messaging instance and set up background message handler
        const messaging = firebase.messaging();
        
        // Handle background messages - this will be called when a push notification arrives
        // while the page is in the background or closed
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
    } catch (error) {
        console.error('Error initializing Firebase in service worker:', error);
    }
} else {
    console.warn('Firebase configuration not available in service worker');
}

// Service worker installation handler - activate immediately
self.addEventListener('install', (event) => {
    console.log('Service worker installing');
    // Skip waiting to activate immediately
    self.skipWaiting();
});

// Service worker activation handler
self.addEventListener('activate', (event) => {
    console.log('Service worker activated');
    // Claim all clients immediately so the service worker becomes active right away
    event.waitUntil(self.clients.claim());
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
