// Give Food Service Worker for Web Push Notifications
// This file must be served from the root of the website

// Firebase SDKs loaded from Google's CDN as recommended by Firebase documentation.
// SRI hashes are not provided by Firebase for their CDN-hosted SDKs.
importScripts('https://www.gstatic.com/firebasejs/9.22.0/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/9.22.0/firebase-messaging-compat.js');

// Firebase configuration will be set when receiving the first push
let firebaseInitialized = false;

// Handle background push messages
self.addEventListener('push', function(event) {
    if (event.data) {
        try {
            const data = event.data.json();
            const notification = data.notification || {};
            const title = notification.title || 'Give Food';
            const options = {
                body: notification.body || '',
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
