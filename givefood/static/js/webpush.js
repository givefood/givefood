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
        statusDiv.innerHTML = 'Your browser does not support notifications';
        subscribeBtn.style.display = 'none';
        return;
    }
    
    // Check if service workers are supported
    if (!('serviceWorker' in navigator)) {
        statusDiv.innerHTML = 'Your browser does not support service workers required for notifications';
        subscribeBtn.style.display = 'none';
        return;
    }
    
    // Update button state based on current permission
    updateButtonState(subscribeBtn, statusDiv, foodbankUuid);
    
    // Handle subscribe/unsubscribe button click
    subscribeBtn.addEventListener('click', function() {
        subscribeBtn.disabled = true;
        subscribeBtn.classList.add('is-loading');
        statusDiv.innerHTML = '';
        
        // Check if already subscribed to determine action
        var subscribedFoodbanks = JSON.parse(localStorage.getItem('gf_webpush_foodbanks') || '[]');
        var isSubscribed = subscribedFoodbanks.indexOf(foodbankUuid) !== -1;
        
        // Fetch Firebase config and subscribe/unsubscribe
        fetch(configUrl)
            .then(function(response) {
                return response.json();
            })
            .then(function(config) {
                if (isSubscribed) {
                    return unsubscribeFromNotifications(foodbankUuid, config, subscribeBtn, statusDiv);
                } else {
                    return subscribeToNotifications(foodbankUuid, config, subscribeBtn, statusDiv);
                }
            })
            .catch(function(error) {
                console.error('Error with notifications:', error);
                statusDiv.innerHTML = 'Failed. Please try again.';
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
            subscribeBtn.textContent = 'Disable notifications';
            subscribeBtn.disabled = false;
            subscribeBtn.classList.remove('is-light', 'is-link');
            subscribeBtn.classList.add('is-success');
        }
    } else if (Notification.permission === 'denied') {
        statusDiv.innerHTML = 'Notifications are blocked. Please enable them in your browser settings.';
        subscribeBtn.style.display = 'none';
    }
}

function subscribeToNotifications(foodbankUuid, config, subscribeBtn, statusDiv) {
    // Request notification permission
    return Notification.requestPermission().then(function(permission) {
        if (permission !== 'granted') {
            statusDiv.innerHTML = 'Notification permission was not granted.';
            subscribeBtn.disabled = false;
            subscribeBtn.classList.remove('is-loading');
            return;
        }
        
        // Register service worker (Firebase's default filename)
        return navigator.serviceWorker.register('/firebase-messaging-sw.js', { scope: '/' })
            .then(function(registration) {
                // Wait for service worker to be ready
                return navigator.serviceWorker.ready;
            })
            .then(function(registration) {
                // Initialize Firebase in the main page
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
                
                // Store token for later use (unsubscribe)
                localStorage.setItem('gf_webpush_token', token);
                
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
                
                statusDiv.innerHTML = 'Successfully subscribed to notifications';
                subscribeBtn.textContent = 'Disable notifications';
                subscribeBtn.disabled = false;
                subscribeBtn.classList.remove('is-loading', 'is-light', 'is-link');
                subscribeBtn.classList.add('is-success');
            })
            .catch(function(error) {
                console.error('Subscription error:', error);
                statusDiv.innerHTML = 'Failed to subscribe: ' + error.message;
                subscribeBtn.disabled = false;
                subscribeBtn.classList.remove('is-loading');
            });
    });
}

function unsubscribeFromNotifications(foodbankUuid, config, subscribeBtn, statusDiv) {
    // Get stored token
    var token = localStorage.getItem('gf_webpush_token');
    
    if (!token) {
        // If no token stored, we need to get one first
        return navigator.serviceWorker.ready
            .then(function(registration) {
                // Initialize Firebase if needed
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
                
                return messaging.getToken({
                    vapidKey: config.vapidKey,
                    serviceWorkerRegistration: registration
                });
            })
            .then(function(newToken) {
                token = newToken;
                localStorage.setItem('gf_webpush_token', token);
                return performUnsubscribe(token, foodbankUuid, subscribeBtn, statusDiv);
            })
            .catch(function(error) {
                console.error('Error getting token for unsubscribe:', error);
                // Even if we can't unsubscribe on server, remove from local storage
                removeFromLocalStorage(foodbankUuid);
                resetButtonToSubscribe(subscribeBtn, statusDiv);
            });
    }
    
    return performUnsubscribe(token, foodbankUuid, subscribeBtn, statusDiv);
}

function performUnsubscribe(token, foodbankUuid, subscribeBtn, statusDiv) {
    const topic = 'foodbank-' + foodbankUuid;
    
    return fetch('/needs/notifications/unsubscribe/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            token: token,
            topic: topic
        })
    })
    .then(function(response) {
        if (!response.ok) {
            throw new Error('Server unsubscription failed');
        }
        return response.json();
    })
    .then(function(result) {
        // Success! Remove this food bank from the list
        removeFromLocalStorage(foodbankUuid);
        
        statusDiv.innerHTML = 'Successfully unsubscribed from notifications';
        resetButtonToSubscribe(subscribeBtn, statusDiv);
    })
    .catch(function(error) {
        console.error('Unsubscription error:', error);
        statusDiv.innerHTML = 'Failed to unsubscribe: ' + error.message;
        subscribeBtn.disabled = false;
        subscribeBtn.classList.remove('is-loading');
    });
}

function removeFromLocalStorage(foodbankUuid) {
    var subscribedFoodbanks = JSON.parse(localStorage.getItem('gf_webpush_foodbanks') || '[]');
    var index = subscribedFoodbanks.indexOf(foodbankUuid);
    if (index !== -1) {
        subscribedFoodbanks.splice(index, 1);
        localStorage.setItem('gf_webpush_foodbanks', JSON.stringify(subscribedFoodbanks));
    }
}

function resetButtonToSubscribe(subscribeBtn, statusDiv) {
    subscribeBtn.textContent = 'Get browser notifications';
    subscribeBtn.disabled = false;
    subscribeBtn.classList.remove('is-loading', 'is-success');
    subscribeBtn.classList.add('is-light', 'is-link');
}
