// Give Food Web Push Notifications using Firebase Cloud Messaging

// Initialize the web push subscription
function initWebPush(foodbankUuid, configUrl) {
    const subscribeBtn = document.getElementById('webpush-subscribe-btn');
    const statusDiv = document.getElementById('webpush-status');
    
    if (!subscribeBtn || !statusDiv) {
        return;
    }
    
    // Check if browser supports notifications
    if (!('Notification' in window)) {
        statusDiv.innerHTML = '<div class="notification is-warning">Your browser does not support notifications.</div>';
        subscribeBtn.style.display = 'none';
        return;
    }
    
    // Check if service workers are supported
    if (!('serviceWorker' in navigator)) {
        statusDiv.innerHTML = '<div class="notification is-warning">Your browser does not support service workers required for notifications.</div>';
        subscribeBtn.style.display = 'none';
        return;
    }
    
    // Update button state based on current permission
    updateButtonState(subscribeBtn, statusDiv, foodbankUuid);
    
    // Handle subscribe button click
    subscribeBtn.addEventListener('click', function() {
        subscribeBtn.disabled = true;
        subscribeBtn.classList.add('is-loading');
        statusDiv.innerHTML = '';
        
        // Fetch Firebase config and subscribe
        fetch(configUrl)
            .then(function(response) {
                return response.json();
            })
            .then(function(config) {
                return subscribeToNotifications(foodbankUuid, config, subscribeBtn, statusDiv);
            })
            .catch(function(error) {
                console.error('Error subscribing to notifications:', error);
                statusDiv.innerHTML = '<div class="notification is-danger">Failed to subscribe. Please try again.</div>';
                subscribeBtn.disabled = false;
                subscribeBtn.classList.remove('is-loading');
            });
    });
}

function updateButtonState(subscribeBtn, statusDiv, foodbankUuid) {
    if (Notification.permission === 'granted') {
        // Check if already subscribed to this specific food bank
        var subscribedFoodbanks = JSON.parse(localStorage.getItem('gf_webpush_foodbanks') || '[]');
        if (subscribedFoodbanks.indexOf(foodbankUuid) !== -1) {
            subscribeBtn.textContent = 'Notifications enabled';
            subscribeBtn.disabled = true;
            subscribeBtn.classList.remove('is-light');
            subscribeBtn.classList.add('is-success');
        }
    } else if (Notification.permission === 'denied') {
        statusDiv.innerHTML = '<div class="notification is-warning">Notifications are blocked. Please enable them in your browser settings.</div>';
        subscribeBtn.style.display = 'none';
    }
}

function subscribeToNotifications(foodbankUuid, config, subscribeBtn, statusDiv) {
    // Request notification permission
    return Notification.requestPermission().then(function(permission) {
        if (permission !== 'granted') {
            statusDiv.innerHTML = '<div class="notification is-warning">Notification permission was not granted.</div>';
            subscribeBtn.disabled = false;
            subscribeBtn.classList.remove('is-loading');
            return;
        }
        
        // Register service worker
        return navigator.serviceWorker.register('/sw.js', { scope: '/' })
            .then(function(registration) {
                // Wait for service worker to be ready
                return navigator.serviceWorker.ready;
            })
            .then(function(registration) {
                // Initialize Firebase
                if (!firebase.apps.length) {
                    firebase.initializeApp({
                        apiKey: config.apiKey,
                        authDomain: config.authDomain,
                        projectId: config.projectId,
                        storageBucket: config.storageBucket,
                        messagingSenderId: config.messagingSenderId,
                        appId: config.appId
                    });
                }
                
                const messaging = firebase.messaging();
                
                // Get FCM token
                return messaging.getToken({
                    vapidKey: config.vapidKey,
                    serviceWorkerRegistration: registration
                });
            })
            .then(function(token) {
                if (!token) {
                    throw new Error('No FCM token received');
                }
                
                // Subscribe to the foodbank topic on the server
                const topic = 'foodbank-' + foodbankUuid;
                return fetch('/needs/notifications/subscribe/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        token: token,
                        topic: topic
                    })
                }).then(function(response) {
                    if (!response.ok) {
                        throw new Error('Server subscription failed');
                    }
                    return response.json();
                });
            })
            .then(function(result) {
                // Success! Store this food bank in the list of subscribed food banks
                var subscribedFoodbanks = JSON.parse(localStorage.getItem('gf_webpush_foodbanks') || '[]');
                if (subscribedFoodbanks.indexOf(foodbankUuid) === -1) {
                    subscribedFoodbanks.push(foodbankUuid);
                    localStorage.setItem('gf_webpush_foodbanks', JSON.stringify(subscribedFoodbanks));
                }
                
                statusDiv.innerHTML = '<div class="notification is-success">Successfully subscribed to notifications!</div>';
                subscribeBtn.textContent = 'Notifications enabled';
                subscribeBtn.disabled = true;
                subscribeBtn.classList.remove('is-loading', 'is-light');
                subscribeBtn.classList.add('is-success');
            })
            .catch(function(error) {
                console.error('Subscription error:', error);
                statusDiv.innerHTML = '<div class="notification is-danger">Failed to subscribe: ' + error.message + '</div>';
                subscribeBtn.disabled = false;
                subscribeBtn.classList.remove('is-loading');
            });
    });
}
