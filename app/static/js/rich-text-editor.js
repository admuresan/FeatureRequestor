/**
 * Reusable Rich Text Editor using Quill.js
 * Free, open-source, no API key required
 */

// Initialize all rich text editors when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Find all textareas with the rich-text-editor class
    const richTextAreas = document.querySelectorAll('textarea.rich-text-editor');
    
    richTextAreas.forEach(function(textarea) {
        // Create a container div for Quill
        const editorContainer = document.createElement('div');
        editorContainer.className = 'rich-text-editor-container';
        editorContainer.style.minHeight = textarea.getAttribute('data-height') || '300px';
        
        // Insert the container after the textarea
        textarea.parentNode.insertBefore(editorContainer, textarea.nextSibling);
        
        // Hide the original textarea
        textarea.style.display = 'none';
        
        // Initialize Quill editor
        const quill = new Quill(editorContainer, {
            theme: 'snow',
            modules: {
                toolbar: [
                    [{ 'header': [1, 2, 3, false] }],
                    ['bold', 'italic', 'underline', 'strike'],
                    [{ 'color': [] }, { 'background': [] }],
                    [{ 'list': 'ordered'}, { 'list': 'bullet' }],
                    [{ 'align': [] }],
                    ['link', 'image'],
                    ['clean']
                ]
            },
            placeholder: textarea.getAttribute('placeholder') || 'Start typing...'
        });
        
        // Set initial content if textarea has value
        if (textarea.value) {
            quill.root.innerHTML = textarea.value;
        }
        
        // Update textarea value when Quill content changes
        quill.on('text-change', function() {
            textarea.value = quill.root.innerHTML;
        });
        
        // Also update textarea before form submission to ensure latest content
        const form = textarea.closest('form');
        if (form) {
            form.addEventListener('submit', function() {
                textarea.value = quill.root.innerHTML;
            });
        }
        
        // Store Quill instance on textarea for easy access
        textarea.quillInstance = quill;
        
        // Handle image paste/insert
        quill.getModule('toolbar').addHandler('image', function() {
            const input = document.createElement('input');
            input.setAttribute('type', 'file');
            input.setAttribute('accept', 'image/*');
            input.click();
            
            input.onchange = function() {
                const file = input.files[0];
                if (file) {
                    const reader = new FileReader();
                    reader.onload = function(e) {
                        const range = quill.getSelection(true);
                        quill.insertEmbed(range.index, 'image', e.target.result);
                    };
                    reader.readAsDataURL(file);
                }
            };
        });
    });
});

/**
 * Get HTML content from a rich text editor
 * @param {string|HTMLElement} selector - CSS selector or textarea element
 * @returns {string} HTML content
 */
function getRichTextContent(selector) {
    const textarea = typeof selector === 'string' ? document.querySelector(selector) : selector;
    if (textarea && textarea.quillInstance) {
        return textarea.quillInstance.root.innerHTML;
    }
    return textarea ? textarea.value : '';
}

/**
 * Set HTML content in a rich text editor
 * @param {string|HTMLElement} selector - CSS selector or textarea element
 * @param {string} html - HTML content to set
 */
function setRichTextContent(selector, html) {
    const textarea = typeof selector === 'string' ? document.querySelector(selector) : selector;
    if (textarea && textarea.quillInstance) {
        textarea.quillInstance.root.innerHTML = html;
        textarea.value = html;
    } else if (textarea) {
        textarea.value = html;
    }
}

