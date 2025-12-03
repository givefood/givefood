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
// messaging must be at module scope to persist and be accessible globally
let messaging = null;

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
    messaging = firebase.messaging();
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

// Fallback push event listener
// This handles raw push events (like DevTools test messages) and edge cases
// where FCM doesn't auto-display notifications
// FCM messages with 'notification' field are handled by FCM's own listener
self.addEventListener('push', (event) => {
    console.log('[Service Worker] Push event received:', event);
    
    if (!event.data) {
        console.log('[Service Worker] Push event has no data');
        return;
    }
    
    try {
        const data = event.data.json();
        console.log('[Service Worker] Push data:', data);
        
        // If this is an FCM message with notification field, FCM should handle it
        // But we'll handle it as fallback if it has our expected structure
        if (data.fcmMessageId && data.notification) {
            console.log('[Service Worker] FCM notification message, letting FCM handle it');
            return;
        }
        
        // Handle the notification ourselves
        const title = data.notification?.title || data.title || 'Food Bank Update';
        const options = {
            body: data.notification?.body || data.body || 'New items needed',
            icon: '/static/img/logo.svg',
            badge: '/static/img/logo.svg',
            data: data.data || data,
        };
        
        event.waitUntil(
            self.registration.showNotification(title, options)
        );
    } catch (e) {
        // If it's not JSON, show a basic notification with the text
        console.log('[Service Worker] Push is not JSON, showing basic notification');
        event.waitUntil(
            self.registration.showNotification('Food Bank Update', {
                body: event.data.text(),
                icon: '/static/img/logo.svg',
            })
        );
    }
});

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
