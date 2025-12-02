/**
 * Firebase Cloud Messaging Service Worker
 * Handles background push notifications for food bank updates
 */

// Import Firebase scripts for service worker
importScripts('https://www.gstatic.com/firebasejs/9.22.0/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/9.22.0/firebase-messaging-compat.js');

// Firebase configuration will be set via message from main thread
let firebaseConfig = null;

// Listen for configuration from main thread
self.addEventListener('message', (event) => {
    if (event.data && event.data.type === 'FIREBASE_CONFIG') {
        firebaseConfig = event.data.config;
        
        // Initialize Firebase with received config
        if (firebaseConfig) {
            firebase.initializeApp(firebaseConfig);
            
            // Get messaging instance
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
    }
});

// Handle notification click
self.addEventListener('notificationclick', (event) => {
    event.notification.close();
    
    // Get the food bank slug from notification data
    const foodbankSlug = event.notification.data?.foodbank_slug;
    
    if (foodbankSlug) {
        const url = `https://www.givefood.org.uk/needs/at/${foodbankSlug}/`;
        
        event.waitUntil(
            clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
                // Check if there's already a window open with this URL
                for (const client of clientList) {
                    if (client.url === url && 'focus' in client) {
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
