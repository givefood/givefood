/**
 * Push Notification Service Worker
 * Handles background push notifications for food bank updates
 * 
 * IMPORTANT: For Firebase Cloud Messaging to work with web push notifications:
 * 1. This service worker must initialize Firebase Messaging
 * 2. For messages with 'notification' field (sent from backend), FCM displays them automatically
 * 3. For data-only messages, onBackgroundMessage handler is called
 * 4. The messaging instance MUST be created for FCM to intercept push events
 */

// Import Firebase scripts for push messaging
importScripts('https://www.gstatic.com/firebasejs/9.22.0/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/9.22.0/firebase-messaging-compat.js');

// Firebase configuration will be injected here by the server
// FIREBASE_CONFIG_PLACEHOLDER

// Initialize Firebase and set up messaging
// This MUST happen at the top level for Firebase to intercept push events
try {
    // Check if config was injected
    if (typeof firebaseConfig === 'undefined' || !firebaseConfig) {
        console.error('Firebase configuration not available in service worker');
        throw new Error('Missing Firebase configuration');
    }
    
    // Validate required config fields
    if (!firebaseConfig.apiKey || !firebaseConfig.projectId ||
        !firebaseConfig.messagingSenderId || !firebaseConfig.appId) {
        console.error('Firebase configuration incomplete:', firebaseConfig);
        throw new Error('Incomplete Firebase configuration');
    }
    
    // Initialize Firebase app
    // This is required for Firebase Messaging to work
    firebase.initializeApp(firebaseConfig);
    console.log('[Service Worker] Firebase initialized successfully');
    
    // Create messaging instance
    // This is CRITICAL - without this, FCM won't handle push notifications
    // FCM uses this to intercept push events and handle notification display
    const messaging = firebase.messaging();
    console.log('[Service Worker] Firebase Messaging instance created');
    
    // Set up background message handler
    // NOTE: This is ONLY called for data-only messages (no 'notification' field)
    // Messages with 'notification' field are displayed automatically by FCM
    messaging.onBackgroundMessage((payload) => {
        console.log('[Service Worker] Received background data message:', payload);
        
        // Extract notification details from data payload
        const notificationTitle = payload.data?.title || 'Food Bank Update';
        const notificationOptions = {
            body: payload.data?.body || 'New items needed',
            icon: '/static/img/logo.svg',
            badge: '/static/img/logo.svg',
            data: payload.data,
        };
        
        // Display notification manually for data-only messages
        return self.registration.showNotification(notificationTitle, notificationOptions);
    });
    
    console.log('[Service Worker] Background message handler registered');
} catch (error) {
    console.error('[Service Worker] Error initializing Firebase:', error);
    console.error('[Service Worker] Error details:', error.message, error.stack);
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

// NOTE: We do NOT add a custom 'push' event listener here!
// Firebase Messaging SDK adds its own 'push' listener when firebase.messaging() is called.
// If we add our own listener, we would need to manually handle notification display,
// which would bypass FCM's automatic handling for notification messages.
// The messaging instance created above is sufficient for FCM to work.

// Handle notification click
self.addEventListener('notificationclick', (event) => {
    console.log('[Service Worker] Notification clicked:', event.notification);
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
