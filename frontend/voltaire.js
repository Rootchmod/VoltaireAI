// frontend/voltaire.js
(function() {
    'use strict';

    const BASE_URL = window.VOLTAIRE_BASE_URL || 'http://localhost:8000';
    const state = {
        dialogVisible: false,
        messages: [],
        siteId: 'default'
    };

    function init() {
        console.log('VoltaireAI initializing...');
        injectStyles();
        createFloatingButton();
        createDialog();
        console.log('VoltaireAI initialized');
    }

    function injectStyles() {
        const style = document.createElement('style');
        style.textContent = `
            /* Floating Button Styles */
            .voltaire-floating-btn {
                position: fixed;
                bottom: 20px;
                right: 20px;
                width: 60px;
                height: 60px;
                z-index: 10000;
                cursor: pointer;
                transition: transform 0.3s;
                user-select: none;
            }
            .voltaire-floating-btn:hover {
                transform: scale(1.1);
            }
            .voltaire-outer-ring {
                position: absolute;
                width: 60px;
                height: 60px;
                border: 2px solid #0066cc;
                border-radius: 50%;
                opacity: 0.6;
                box-sizing: border-box;
            }
            .voltaire-inner-ring {
                position: absolute;
                width: 40px;
                height: 40px;
                border: 3px solid #0066cc;
                border-radius: 50%;
                background: rgba(0,102,204,0.2);
                top: 10px;
                left: 10px;
                box-sizing: border-box;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .voltaire-inner-ring::after {
                content: 'V';
                font-size: 18px;
                font-weight: bold;
                color: #0066cc;
            }

            /* Dialog Styles */
            .voltaire-dialog {
                position: fixed;
                width: 400px;
                height: 500px;
                background: white;
                border-radius: 8px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.15);
                z-index: 9999;
                display: none;
                flex-direction: column;
                bottom: 90px;
                right: 20px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }
            .voltaire-dialog.active {
                display: flex;
            }
            .voltaire-header {
                padding: 15px;
                background: #0066cc;
                color: white;
                border-radius: 8px 8px 0 0;
                display: flex;
                justify-content: space-between;
                align-items: center;
                cursor: move;
                font-weight: 600;
            }
            .voltaire-close {
                cursor: pointer;
                font-size: 24px;
                line-height: 1;
                transition: opacity 0.2s;
            }
            .voltaire-close:hover {
                opacity: 0.8;
            }
            .voltaire-body {
                flex: 1;
                padding: 15px;
                background: #f9f9f9;
                overflow-y: auto;
                display: flex;
                flex-direction: column;
                gap: 10px;
            }
            .voltaire-message {
                display: flex;
                max-width: 100%;
            }
            .voltaire-message.user {
                justify-content: flex-end;
            }
            .voltaire-message.ai {
                justify-content: flex-start;
            }
            .voltaire-content {
                max-width: 80%;
                padding: 10px 15px;
                border-radius: 12px;
                word-wrap: break-word;
                overflow-wrap: break-word;
            }
            .voltaire-message.user .voltaire-content {
                background: #0066cc;
                color: white;
                border-bottom-right-radius: 4px;
            }
            .voltaire-message.ai .voltaire-content {
                background: #e9e9e9;
                color: #333;
                border-bottom-left-radius: 4px;
            }
            .voltaire-content p {
                margin: 0 0 8px 0;
            }
            .voltaire-content p:last-child {
                margin-bottom: 0;
            }
            .voltaire-content code {
                background: rgba(0,0,0,0.1);
                padding: 2px 4px;
                border-radius: 3px;
                font-size: 0.9em;
            }
            .voltaire-content pre {
                background: rgba(0,0,0,0.1);
                padding: 8px;
                border-radius: 4px;
                overflow-x: auto;
                margin: 8px 0;
            }
            .voltaire-content pre code {
                background: none;
                padding: 0;
            }
            .voltaire-footer {
                padding: 15px;
                background: white;
                border-top: 1px solid #ddd;
                display: flex;
                gap: 10px;
                border-radius: 0 0 8px 8px;
            }
            .voltaire-input {
                flex: 1;
                padding: 10px;
                border: 1px solid #ddd;
                border-radius: 4px;
                resize: none;
                font-family: inherit;
                font-size: 14px;
                outline: none;
            }
            .voltaire-input:focus {
                border-color: #0066cc;
            }
            .voltaire-send {
                padding: 10px 20px;
                background: #0066cc;
                color: white;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                font-weight: 600;
                transition: background 0.2s;
            }
            .voltaire-send:hover {
                background: #0052a3;
            }
            .voltaire-send:disabled {
                background: #ccc;
                cursor: not-allowed;
            }
            .voltaire-typing {
                display: flex;
                gap: 4px;
                padding: 10px 15px;
                background: #e9e9e9;
                border-radius: 12px;
                width: fit-content;
            }
            .voltaire-typing span {
                width: 8px;
                height: 8px;
                background: #999;
                border-radius: 50%;
                animation: voltaire-bounce 1.4s infinite ease-in-out both;
            }
            .voltaire-typing span:nth-child(1) { animation-delay: -0.32s; }
            .voltaire-typing span:nth-child(2) { animation-delay: -0.16s; }
            @keyframes voltaire-bounce {
                0%, 80%, 100% { transform: scale(0); }
                40% { transform: scale(1); }
            }
        `;
        document.head.appendChild(style);
    }

    function createFloatingButton() {
        const btn = document.createElement('div');
        btn.className = 'voltaire-floating-btn';
        btn.id = 'voltaire-floating-btn';
        btn.innerHTML = `
            <div class="voltaire-outer-ring"></div>
            <div class="voltaire-inner-ring"></div>
        `;
        btn.addEventListener('click', toggleDialog);
        document.body.appendChild(btn);

        setupDraggable(btn, {
            onDragStart: () => btn.style.opacity = '0.8',
            onDragEnd: () => btn.style.opacity = '1'
        });
    }

    function createDialog() {
        const dialog = document.createElement('div');
        dialog.className = 'voltaire-dialog';
        dialog.id = 'voltaire-dialog';
        dialog.innerHTML = `
            <div class="voltaire-header">
                <span>VoltaireAI Assistant</span>
                <span class="voltaire-close">&times;</span>
            </div>
            <div class="voltaire-body" id="voltaire-messages"></div>
            <div class="voltaire-footer">
                <textarea class="voltaire-input" placeholder="Ask me anything..." rows="2"></textarea>
                <button class="voltaire-send">Send</button>
            </div>
        `;
        document.body.appendChild(dialog);

        setupDialogEvents(dialog);
        setupDraggable(dialog.querySelector('.voltaire-header'), { target: dialog });
    }

    function toggleDialog() {
        const dialog = document.querySelector('.voltaire-dialog');
        state.dialogVisible = !state.dialogVisible;
        dialog.classList.toggle('active', state.dialogVisible);

        if (state.dialogVisible) {
            dialog.querySelector('.voltaire-input').focus();
        }
    }

    function setupDialogEvents(dialog) {
        const closeBtn = dialog.querySelector('.voltaire-close');
        const sendBtn = dialog.querySelector('.voltaire-send');
        const input = dialog.querySelector('.voltaire-input');
        const messagesDiv = dialog.querySelector('#voltaire-messages');

        closeBtn.addEventListener('click', () => {
            dialog.classList.remove('active');
            state.dialogVisible = false;
        });

        sendBtn.addEventListener('click', () => sendMessage(input, messagesDiv, sendBtn));

        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage(input, messagesDiv, sendBtn);
            }
        });
    }

    function sendMessage(input, messagesDiv, sendBtn) {
        const text = input.value.trim();
        if (!text) return;

        // Disable send button while processing
        sendBtn.disabled = true;

        addMessage(messagesDiv, 'user', text);
        input.value = '';

        // Show typing indicator
        const typingId = showTyping(messagesDiv);

        fetch(`${BASE_URL}/api/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text, site_id: state.siteId })
        })
        .then(res => {
            if (!res.ok) {
                throw new Error(`HTTP error! status: ${res.status}`);
            }
            return res.json();
        })
        .then(data => {
            removeTyping(messagesDiv, typingId);
            addMessage(messagesDiv, 'ai', data.message || data.response || 'No response received');
        })
        .catch(err => {
            removeTyping(messagesDiv, typingId);
            addMessage(messagesDiv, 'ai', `Error: ${err.message}`);
            console.error('VoltaireAI Error:', err);
        })
        .finally(() => {
            sendBtn.disabled = false;
            input.focus();
        });
    }

    function addMessage(container, role, text) {
        const div = document.createElement('div');
        div.className = `voltaire-message ${role}`;

        const content = document.createElement('div');
        content.className = 'voltaire-content';

        // Render markdown for AI messages if marked.js is available
        if (role === 'ai' && typeof window.marked !== 'undefined') {
            try {
                content.innerHTML = marked.parse(text);
            } catch (e) {
                content.textContent = text;
            }
        } else {
            content.textContent = text;
        }

        div.appendChild(content);
        container.appendChild(div);
        container.scrollTop = container.scrollHeight;

        state.messages.push({ role, text, timestamp: Date.now() });
    }

    function showTyping(container) {
        const typing = document.createElement('div');
        const id = 'typing-' + Date.now();
        typing.id = id;
        typing.className = 'voltaire-message ai';
        typing.innerHTML = `
            <div class="voltaire-typing">
                <span></span>
                <span></span>
                <span></span>
            </div>
        `;
        container.appendChild(typing);
        container.scrollTop = container.scrollHeight;
        return id;
    }

    function removeTyping(container, id) {
        const typing = document.getElementById(id);
        if (typing) {
            typing.remove();
        }
    }

    function setupDraggable(element, options = {}) {
        let isDragging = false;
        let hasMoved = false;
        let startX, startY, initialX, initialY;
        const target = options.target || element;

        element.addEventListener('mousedown', (e) => {
            isDragging = true;
            hasMoved = false;
            startX = e.clientX;
            startY = e.clientY;

            // Get current position
            const rect = target.getBoundingClientRect();
            initialX = rect.left;
            initialY = rect.top;

            if (options.onDragStart) options.onDragStart();
            e.preventDefault();
        });

        document.addEventListener('mousemove', (e) => {
            if (!isDragging) return;

            const deltaX = e.clientX - startX;
            const deltaY = e.clientY - startY;

            // Check if actual movement occurred
            if (Math.abs(deltaX) > 5 || Math.abs(deltaY) > 5) {
                hasMoved = true;
            }

            if (!hasMoved) return;

            const newX = initialX + deltaX;
            const newY = initialY + deltaY;

            const maxX = window.innerWidth - target.offsetWidth;
            const maxY = window.innerHeight - target.offsetHeight;

            target.style.left = Math.max(0, Math.min(newX, maxX)) + 'px';
            target.style.top = Math.max(0, Math.min(newY, maxY)) + 'px';

            // Remove bottom/right positioning when dragging
            target.style.bottom = 'auto';
            target.style.right = 'auto';
        });

        document.addEventListener('mouseup', () => {
            if (isDragging) {
                if (options.onDragEnd) options.onDragEnd();

                // If moved significantly, prevent click event
                if (hasMoved && element.id === 'voltaire-floating-btn') {
                    element.dataset.preventClick = 'true';
                    setTimeout(() => {
                        element.dataset.preventClick = 'false';
                    }, 100);
                }
            }
            isDragging = false;
            hasMoved = false;
        });
    }

    // Override click handler to check for drag
    document.addEventListener('click', (e) => {
        const btn = document.getElementById('voltaire-floating-btn');
        if (btn && btn.contains(e.target) && btn.dataset.preventClick === 'true') {
            e.stopImmediatePropagation();
        }
    }, true);

    // Initialize on page load
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Expose global API
    window.VoltaireAI = {
        toggle: toggleDialog,
        sendMessage: (msg) => {
            const input = document.querySelector('.voltaire-input');
            const messagesDiv = document.querySelector('#voltaire-messages');
            const sendBtn = document.querySelector('.voltaire-send');
            if (msg && typeof msg === 'string') {
                input.value = msg;
            }
            sendMessage(input, messagesDiv, sendBtn);
        },
        setSiteId: (id) => { state.siteId = id; },
        getState: () => ({ ...state })
    };
})();