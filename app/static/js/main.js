// IMPORTANT: Read instructions/architecture before making changes to this file
// Main JavaScript file
// Error handling functions are imported from error-handling.js

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    // Ensure error handling functions are loaded (they should be loaded before this script)
    if (typeof initializeFlashMessages === 'function') {
        initializeFlashMessages();
        
        // Watch for dynamically added flash messages
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                mutation.addedNodes.forEach(function(node) {
                    if (node.nodeType === 1) { // Element node
                        // Check if the added node is a flash message or contains flash messages
                        if (node.classList && node.classList.contains('flash-message')) {
                            initializeFlashMessages();
                        } else if (node.querySelectorAll) {
                            const flashMessages = node.querySelectorAll('.flash-message');
                            if (flashMessages.length > 0) {
                                initializeFlashMessages();
                            }
                        }
                    }
                });
            });
        });
        
        // Observe the document body for changes
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }
});

