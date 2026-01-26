// Error handling and flash message management
// This module handles the display and dismissal of flash messages, including error messages

// Function to check and remove empty flash-messages container
function checkAndRemoveFlashContainer() {
    const flashContainer = document.querySelector('.flash-messages');
    if (flashContainer) {
        const remainingMessages = flashContainer.querySelectorAll('.flash-message');
        if (remainingMessages.length === 0) {
            flashContainer.style.transition = 'opacity 0.5s';
            flashContainer.style.opacity = '0';
            setTimeout(function() {
                flashContainer.remove();
            }, 500);
        }
    }
}

// Function to initialize flash messages (can be called for dynamically added messages too)
function initializeFlashMessages() {
    const flashMessages = document.querySelectorAll('.flash-message:not(.initialized)');
    
    flashMessages.forEach(function(message) {
        // Mark as initialized to avoid duplicate processing
        message.classList.add('initialized');
        
        // Check if this is an error message
        const isError = message.classList.contains('flash-error');
        
        if (isError) {
            // For error messages, add a dismiss button and don't auto-hide
            // Check if dismiss button already exists
            if (!message.querySelector('.flash-dismiss')) {
                const dismissButton = document.createElement('button');
                dismissButton.className = 'flash-dismiss';
                dismissButton.innerHTML = '×';
                dismissButton.setAttribute('aria-label', 'Dismiss error');
                dismissButton.onclick = function() {
                    message.style.transition = 'opacity 0.5s';
                    message.style.opacity = '0';
                    setTimeout(function() {
                        message.remove();
                        checkAndRemoveFlashContainer();
                    }, 500);
                };
                message.appendChild(dismissButton);
            }
        } else {
            // For non-error messages, auto-hide after 5 seconds
            setTimeout(function() {
                message.style.transition = 'opacity 0.5s';
                message.style.opacity = '0';
                setTimeout(function() {
                    message.remove();
                    checkAndRemoveFlashContainer();
                }, 500);
            }, 5000);
        }
    });
}

// Make functions available globally
window.checkAndRemoveFlashContainer = checkAndRemoveFlashContainer;
window.initializeFlashMessages = initializeFlashMessages;

