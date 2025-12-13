// Give Food Web Push Notifications using VAPID (django-webpush)
// This replaces the Firebase-based web push with standard Web Push API

// Initialize the web push subscription
function initWebPush(foodbankSlug, configUrl) {
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
    
    // Check if PushManager is supported
    if (!('PushManager' in window)) {
        statusDiv.innerHTML = 'Your browser does not support push notifications';
        subscribeBtn.style.display = 'none';
        return;
    }
    
    // Update button state based on current permission
    updateButtonState(subscribeBtn, statusDiv, foodbankSlug);
    
    // Handle subscribe/unsubscribe button click
    subscribeBtn.addEventListener('click', function() {
        subscribeBtn.disabled = true;
        subscribeBtn.classList.add('is-loading');
        statusDiv.innerHTML = '';
        
        // Check if already subscribed to determine action
        var subscribedFoodbanks = JSON.parse(localStorage.getItem('gf_webpush_foodbanks') || '[]');
        var isSubscribed = subscribedFoodbanks.indexOf(foodbankSlug) !== -1;
        
        // Fetch VAPID config and subscribe/unsubscribe
        fetch(configUrl)
            .then(function(response) {
                return response.json();
            })
            .then(function(config) {
                if (isSubscribed) {
                    return unsubscribeFromNotifications(foodbankSlug, subscribeBtn, statusDiv);
                } else {
                    return subscribeToNotifications(foodbankSlug, config, subscribeBtn, statusDiv);
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

function updateButtonState(subscribeBtn, statusDiv, foodbankSlug) {
    if (Notification.permission === 'granted') {
        // Check if already subscribed to this specific food bank
        var subscribedFoodbanks = JSON.parse(localStorage.getItem('gf_webpush_foodbanks') || '[]');
        if (subscribedFoodbanks.indexOf(foodbankSlug) !== -1) {
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

// Convert base64 URL-safe string to Uint8Array for applicationServerKey
function urlBase64ToUint8Array(base64String) {
    var padding = '='.repeat((4 - base64String.length % 4) % 4);
    var base64 = (base64String + padding)
        .replace(/-/g, '+')
        .replace(/_/g, '/');
    
    var rawData = window.atob(base64);
    var outputArray = new Uint8Array(rawData.length);
    
    for (var i = 0; i < rawData.length; ++i) {
        outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
}

function subscribeToNotifications(foodbankSlug, config, subscribeBtn, statusDiv) {
    // Request notification permission
    return Notification.requestPermission().then(function(permission) {
        if (permission !== 'granted') {
            statusDiv.innerHTML = 'Notification permission was not granted.';
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
                // Subscribe to push with VAPID public key
                var applicationServerKey = urlBase64ToUint8Array(config.vapidPublicKey);
                
                return registration.pushManager.subscribe({
                    userVisibleOnly: true,
                    applicationServerKey: applicationServerKey
                });
            })
            .then(function(subscription) {
                // Extract subscription data
                var subscriptionJson = subscription.toJSON();
                var endpoint = subscriptionJson.endpoint;
                var p256dh = subscriptionJson.keys.p256dh;
                var auth = subscriptionJson.keys.auth;
                
                // Store subscription endpoint for unsubscribe
                localStorage.setItem('gf_webpush_endpoint', endpoint);
                
                // Send subscription to server
                return fetch('/needs/webpush/subscribe/' + foodbankSlug + '/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        endpoint: endpoint,
                        p256dh: p256dh,
                        auth: auth,
                        browser: navigator.userAgent
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
                if (subscribedFoodbanks.indexOf(foodbankSlug) === -1) {
                    subscribedFoodbanks.push(foodbankSlug);
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

function unsubscribeFromNotifications(foodbankSlug, subscribeBtn, statusDiv) {
    var endpoint = localStorage.getItem('gf_webpush_endpoint');
    
    return navigator.serviceWorker.ready
        .then(function(registration) {
            return registration.pushManager.getSubscription();
        })
        .then(function(subscription) {
            if (subscription) {
                // Unsubscribe from browser
                return subscription.unsubscribe().then(function() {
                    return subscription.endpoint;
                });
            }
            return endpoint;
        })
        .then(function(endpointToRemove) {
            if (!endpointToRemove) {
                throw new Error('No subscription found');
            }
            
            // Notify server
            return fetch('/needs/webpush/unsubscribe/' + foodbankSlug + '/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    endpoint: endpointToRemove
                })
            });
        })
        .then(function(response) {
            if (!response.ok) {
                throw new Error('Server unsubscription failed');
            }
            return response.json();
        })
        .then(function(result) {
            // Success! Remove this food bank from the list
            removeFromLocalStorage(foodbankSlug);
            localStorage.removeItem('gf_webpush_endpoint');
            
            statusDiv.innerHTML = 'Successfully unsubscribed from notifications';
            resetButtonToSubscribe(subscribeBtn, statusDiv);
        })
        .catch(function(error) {
            console.error('Unsubscription error:', error);
            // Even if server fails, remove from local storage
            removeFromLocalStorage(foodbankSlug);
            statusDiv.innerHTML = 'Unsubscribed from notifications';
            resetButtonToSubscribe(subscribeBtn, statusDiv);
        });
}

function removeFromLocalStorage(foodbankSlug) {
    var subscribedFoodbanks = JSON.parse(localStorage.getItem('gf_webpush_foodbanks') || '[]');
    var index = subscribedFoodbanks.indexOf(foodbankSlug);
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
