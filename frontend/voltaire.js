// frontend/voltaire.js
(function() {
    'use strict';

    const BASE_URL = window.VOLTAIRE_BASE_URL || 'http://localhost:8001';
    const MARKED_CDN = 'https://cdn.jsdelivr.net/npm/marked/marked.min.js';
    const TESTING_LIBRARY_CDN = 'https://cdn.jsdelivr.net/npm/@testing-library/dom/dist/@testing-library/dom.umd.min.js';

    const state = {
        dialogVisible: false,
        messages: [],
        siteId: window.location.hostname || 'default',
        scanning: false,
        scanStatus: 'idle', // idle | scanning | uploading | ready | error
        scanError: null,
        executing: false,
        checklist: null
    };

    // ── Init ──────────────────────────────────────────────
    function init() {
        console.log('VoltaireAI initializing...');
        injectStyles();
        createFloatingButton();
        createDialog();
        loadMarked();
        loadTestingLibrary();
        // Scan DOM after a short delay to let page load
        setTimeout(scanAndUploadDOM, 2000);
        console.log('VoltaireAI initialized');
    }

    // ── Marked (CDN) ──────────────────────────────────────
    function loadMarked() {
        if (typeof window.marked !== 'undefined') return;
        const script = document.createElement('script');
        script.src = MARKED_CDN;
        script.async = true;
        document.head.appendChild(script);
    }

    // ── Testing Library (CDN) ─────────────────────────────
    function loadTestingLibrary() {
        if (window._tlReady) return;
        function expose() {
            if (typeof window.TestingLibraryDom !== 'undefined' && window.TestingLibraryDom.screen) {
                window.screen = window.TestingLibraryDom.screen;
                window.fireEvent = window.TestingLibraryDom.fireEvent;
                window.waitFor = window.TestingLibraryDom.waitFor;
                window.within = window.TestingLibraryDom.within;
                window._tlReady = true;
                console.log('VoltaireAI: Testing Library ready');
            }
        }
        if (typeof window.TestingLibraryDom !== 'undefined') {
            expose();
            return;
        }
        const script = document.createElement('script');
        script.src = TESTING_LIBRARY_CDN;
        script.async = true;
        script.onload = expose;
        document.head.appendChild(script);
    }

    // ── DOM Scanner ───────────────────────────────────────
    function scanAndUploadDOM() {
        if (state.scanning) return;
        state.scanning = true;
        state.scanStatus = 'scanning';

        try {
            const elements = [];
            const selectors = ['button', 'a', 'input', 'select', 'textarea',
                '[role="button"]', '[role="link"]', '[tabindex]'];

            document.querySelectorAll(selectors.join(',')).forEach(el => {
                // Skip hidden/invisible elements
                if (el.offsetParent === null && el.getAttribute('aria-hidden') !== 'false') return;
                if (el.getAttribute('aria-hidden') === 'true') return;

                elements.push({
                    id: 'elem_' + elements.length,
                    type: el.tagName.toLowerCase(),
                    selector: getCSSSelector(el),
                    text: (el.textContent || el.value || '').trim().substring(0, 120),
                    actions: getAvailableActions(el),
                    attributes: {
                        name: el.getAttribute('name') || '',
                        placeholder: el.getAttribute('placeholder') || '',
                        href: el.getAttribute('href') || ''
                    }
                });

                if (elements.length >= 200) return; // Safety limit
            });

            if (elements.length === 0) {
                state.scanStatus = 'ready';
                state.scanning = false;
                return;
            }

            state.scanStatus = 'uploading';

            fetch(BASE_URL + '/VoltaireAI/upload-dom', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    category: 'sitemap',
                    name: 'default',
                    elements: elements
                }),
                signal: AbortSignal.timeout(10000) // 10s timeout
            })
            .then(function(r) {
                if (!r.ok) throw new Error('HTTP ' + r.status);
                return r.json();
            })
            .then(function(data) {
                state.scanStatus = 'ready';
                state.scanError = null;
                console.log('VoltaireAI: DOM uploaded', data.element_count, 'elements');
                // If dialog is open, show status
                if (state.dialogVisible) {
                    addSystemMessage('知识库已就绪 (' + data.element_count + ' 个元素)');
                }
            })
            .catch(function(err) {
                state.scanStatus = 'error';
                state.scanError = err.message;
                console.warn('VoltaireAI: DOM upload failed', err);
                if (state.dialogVisible) {
                    addSystemMessage('知识库连接失败: ' + err.message + '。部分功能可能不可用。');
                }
            });

        } finally {
            state.scanning = false;
        }
    }

    function getCSSSelector(el) {
        if (el.id) return '#' + CSS.escape(el.id);

        const parts = [];
        let current = el;

        while (current && current !== document.body && current !== document.documentElement) {
            let selector = current.tagName.toLowerCase();
            if (current.id) {
                parts.unshift('#' + CSS.escape(current.id));
                break;
            }
            if (current.className && typeof current.className === 'string') {
                const cls = current.className.trim().split(/\s+/).filter(c => c).slice(0, 2);
                if (cls.length) selector += '.' + cls.map(c => CSS.escape(c)).join('.');
            }
            // Add nth-child for disambiguation
            const parent = current.parentElement;
            if (parent) {
                const siblings = Array.from(parent.children).filter(
                    s => s.tagName === current.tagName
                );
                if (siblings.length > 1) {
                    const index = siblings.indexOf(current) + 1;
                    selector += ':nth-child(' + index + ')';
                }
            }
            parts.unshift(selector);
            current = current.parentElement;
            if (parts.join(' ').length > 100) break; // Safety length
        }
        return parts.join(' > ');
    }

    function getAvailableActions(el) {
        const tag = el.tagName.toLowerCase();
        const type = (el.getAttribute('type') || '').toLowerCase();
        const actions = [];
        if (tag === 'button' || tag === 'a' || type === 'submit' || type === 'button'
            || el.getAttribute('role') === 'button' || el.tagName === 'SELECT') {
            actions.push('click');
        }
        if (tag === 'input' && (type === 'text' || type === 'email' || type === 'password'
            || type === 'search' || type === 'url' || type === 'number' || type === 'tel')) {
            actions.push('fill');
        }
        if (tag === 'textarea') actions.push('fill');
        if (tag === 'select') actions.push('select');
        if (tag === 'input' && type === 'checkbox') actions.push('check');
        if (tag === 'input' && type === 'radio') actions.push('select');
        return actions;
    }

    // ── Styles ────────────────────────────────────────────
    function injectStyles() {
        const style = document.createElement('style');
        style.textContent = `
            /* ── Floating Button ── */
            .voltaire-floating-btn {
                position: fixed;
                bottom: 20px; right: 20px;
                width: 60px; height: 60px;
                z-index: 10000;
                cursor: pointer;
                transition: transform 0.3s;
                user-select: none;
            }
            .voltaire-floating-btn:hover { transform: scale(1.1); }
            .voltaire-outer-ring {
                position: absolute;
                width: 60px; height: 60px;
                border: 2px solid #0066cc;
                border-radius: 50%;
                opacity: 0.6;
                box-sizing: border-box;
            }
            .voltaire-inner-ring {
                position: absolute;
                width: 40px; height: 40px;
                border: 3px solid #0066cc;
                border-radius: 50%;
                background: rgba(0,102,204,0.2);
                top: 10px; left: 10px;
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

            /* ── Dialog ── */
            .voltaire-dialog {
                position: fixed;
                width: 420px;
                height: 520px;
                background: white;
                border-radius: 12px;
                box-shadow: 0 8px 32px rgba(0,0,0,0.18);
                z-index: 9999;
                display: none;
                flex-direction: column;
                bottom: 90px; right: 20px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                overflow: hidden;
            }
            .voltaire-dialog.active { display: flex; }

            .voltaire-header {
                padding: 14px 16px;
                background: #0066cc;
                color: white;
                display: flex;
                justify-content: space-between;
                align-items: center;
                cursor: move;
                font-weight: 600;
                font-size: 15px;
                flex-shrink: 0;
            }
            .voltaire-close {
                cursor: pointer;
                font-size: 22px;
                line-height: 1;
                opacity: 0.8;
                transition: opacity 0.2s;
            }
            .voltaire-close:hover { opacity: 1; }

            .voltaire-body {
                flex: 1;
                padding: 12px;
                background: #f5f5f5;
                overflow-y: auto;
                display: flex;
                flex-direction: column;
                gap: 8px;
            }

            /* ── Messages ── */
            .voltaire-message {
                display: flex;
                max-width: 100%;
                animation: voltaire-fadeIn 0.2s ease;
            }
            @keyframes voltaire-fadeIn {
                from { opacity: 0; transform: translateY(8px); }
                to { opacity: 1; transform: translateY(0); }
            }
            .voltaire-message.user { justify-content: flex-end; }
            .voltaire-message.ai { justify-content: flex-start; }

            .voltaire-content {
                max-width: 85%;
                padding: 10px 14px;
                border-radius: 14px;
                word-wrap: break-word;
                overflow-wrap: break-word;
                line-height: 1.5;
                font-size: 14px;
            }
            .voltaire-message.user .voltaire-content {
                background: #0066cc;
                color: white;
                border-bottom-right-radius: 4px;
            }
            .voltaire-message.ai .voltaire-content {
                background: white;
                color: #333;
                border-bottom-left-radius: 4px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.08);
            }

            /* Markdown content styles */
            .voltaire-content p { margin: 0 0 6px 0; }
            .voltaire-content p:last-child { margin-bottom: 0; }
            .voltaire-content ul, .voltaire-content ol {
                margin: 4px 0; padding-left: 20px;
            }
            .voltaire-content li { margin: 2px 0; }
            .voltaire-content code {
                background: rgba(0,0,0,0.08);
                padding: 2px 5px;
                border-radius: 3px;
                font-size: 0.88em;
                font-family: 'Consolas', 'Courier New', monospace;
            }
            .voltaire-content pre {
                background: #1e1e2e;
                color: #cdd6f4;
                padding: 12px;
                border-radius: 8px;
                overflow-x: auto;
                margin: 8px 0;
                font-size: 13px;
                line-height: 1.45;
            }
            .voltaire-content pre code {
                background: none;
                padding: 0;
                color: inherit;
            }
            .voltaire-content blockquote {
                border-left: 3px solid #0066cc;
                margin: 6px 0;
                padding: 4px 12px;
                color: #666;
            }
            .voltaire-content table {
                border-collapse: collapse;
                margin: 8px 0;
                font-size: 13px;
            }
            .voltaire-content th, .voltaire-content td {
                border: 1px solid #ddd;
                padding: 6px 10px;
                text-align: left;
            }
            .voltaire-content th { background: #f0f0f0; font-weight: 600; }

            /* ── Execution status badges ── */
            .voltaire-exec-badge {
                display: inline-block;
                padding: 2px 8px;
                border-radius: 10px;
                font-size: 11px;
                font-weight: 600;
                margin-top: 6px;
            }
            .voltaire-exec-badge.running {
                background: #fff3cd; color: #856404;
            }
            .voltaire-exec-badge.success {
                background: #d4edda; color: #155724;
            }
            .voltaire-exec-badge.failed {
                background: #f8d7da; color: #721c24;
            }

            /* ── Checklist ── */
            .voltaire-checklist {
                margin: 8px 0 4px 0;
                padding: 0;
                list-style: none;
            }
            .voltaire-checklist-item {
                display: flex;
                align-items: flex-start;
                gap: 8px;
                padding: 6px 8px;
                margin: 3px 0;
                border-radius: 6px;
                background: #fafafa;
                font-size: 13px;
                border: 1px solid #eee;
            }
            .voltaire-checklist-item .check-icon {
                flex-shrink: 0;
                width: 18px; height: 18px;
                border: 2px solid #ccc;
                border-radius: 50%;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                font-size: 11px;
                margin-top: 1px;
                transition: all 0.2s;
            }
            .voltaire-checklist-item.done .check-icon {
                background: #28a745;
                border-color: #28a745;
                color: white;
            }
            .voltaire-checklist-item.failed .check-icon {
                background: #dc3545;
                border-color: #dc3545;
                color: white;
            }
            .voltaire-checklist-item.active .check-icon {
                border-color: #0066cc;
                background: #e8f0fe;
            }
            .voltaire-checklist-item .step-label {
                color: #666;
                font-size: 11px;
                display: block;
                margin-bottom: 1px;
            }

            /* ── Execute button ── */
            .voltaire-exec-btn {
                display: inline-block;
                margin-top: 8px;
                padding: 6px 16px;
                background: #0066cc;
                color: white;
                border: none;
                border-radius: 6px;
                cursor: pointer;
                font-size: 13px;
                font-weight: 600;
                transition: background 0.2s;
            }
            .voltaire-exec-btn:hover { background: #0052a3; }
            .voltaire-exec-btn:disabled { background: #ccc; cursor: not-allowed; }
            .voltaire-exec-btn.warning { background: #e67e22; }
            .voltaire-exec-btn.warning:hover { background: #d35400; }

            /* ── Suggestions ── */
            .voltaire-suggestions {
                padding: 8px 12px;
                background: #fff;
                border-top: 1px solid #f0f0f0;
                display: flex;
                align-items: center;
                gap: 6px;
                flex-wrap: wrap;
                flex-shrink: 0;
            }
            .voltaire-suggestions-label {
                font-size: 12px;
                color: #999;
                white-space: nowrap;
            }
            .voltaire-suggestion-chip {
                display: inline-block;
                padding: 4px 10px;
                font-size: 12px;
                color: #0066cc;
                background: #e6f4ff;
                border: 1px solid #b3d8ff;
                border-radius: 12px;
                cursor: pointer;
                white-space: nowrap;
                transition: all 0.15s;
                user-select: none;
            }
            .voltaire-suggestion-chip:hover {
                background: #b3d8ff;
                color: #004a99;
            }

            /* ── Footer / Input ── */
            .voltaire-footer {
                padding: 12px;
                background: white;
                border-top: 1px solid #e0e0e0;
                display: flex;
                gap: 8px;
                flex-shrink: 0;
            }
            .voltaire-input {
                flex: 1;
                padding: 10px 12px;
                border: 1px solid #ddd;
                border-radius: 8px;
                resize: none;
                font-family: inherit;
                font-size: 14px;
                outline: none;
                transition: border-color 0.2s;
                max-height: 80px;
            }
            .voltaire-input:focus { border-color: #0066cc; }
            .voltaire-send {
                padding: 10px 20px;
                background: #0066cc;
                color: white;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                font-weight: 600;
                transition: background 0.2s;
                white-space: nowrap;
            }
            .voltaire-send:hover { background: #0052a3; }
            .voltaire-send:disabled { background: #ccc; cursor: not-allowed; }

            /* ── Typing indicator ── */
            .voltaire-typing {
                display: flex;
                gap: 4px;
                padding: 12px 16px;
                background: white;
                border-radius: 14px;
                border-bottom-left-radius: 4px;
                width: fit-content;
                box-shadow: 0 1px 3px rgba(0,0,0,0.08);
            }
            .voltaire-typing span {
                width: 8px; height: 8px;
                background: #bbb;
                border-radius: 50%;
                animation: voltaire-bounce 1.4s infinite ease-in-out both;
            }
            .voltaire-typing span:nth-child(1) { animation-delay: -0.32s; }
            .voltaire-typing span:nth-child(2) { animation-delay: -0.16s; }
            .voltaire-typing span:nth-child(3) { animation-delay: 0s; }
            @keyframes voltaire-bounce {
                0%, 80%, 100% { transform: scale(0); }
                40% { transform: scale(1); }
            }
        `;
        document.head.appendChild(style);
    }

    // ── Create UI ────────────────────────────────────────
    function createFloatingButton() {
        const btn = document.createElement('div');
        btn.className = 'voltaire-floating-btn';
        btn.id = 'voltaire-floating-btn';
        btn.innerHTML = '<div class="voltaire-outer-ring"></div><div class="voltaire-inner-ring"></div>';
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
                <span>VoltaireAI</span>
                <span class="voltaire-close">&times;</span>
            </div>
            <div class="voltaire-body" id="voltaire-messages"></div>
            <div class="voltaire-suggestions">
                <span class="voltaire-suggestions-label">演示提问：</span>
                <span class="voltaire-suggestion-chip" data-question="帮我调整一下商品拣货位">帮我调整一下商品拣货位</span>
            </div>
            <div class="voltaire-footer">
                <textarea class="voltaire-input" placeholder="Ask me anything..." rows="1"></textarea>
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
            // Show scan status when dialog opens
            showScanStatus();
        }
    }

    function showScanStatus() {
        if (state.scanStatus === 'ready') return; // Already ready, no need
        if (state.scanStatus === 'error') {
            addSystemMessage('知识库连接失败，点击重试', function() {
                state.scanStatus = 'idle';
                scanAndUploadDOM();
            });
        } else if (state.scanStatus === 'scanning' || state.scanStatus === 'uploading') {
            addSystemMessage('正在扫描页面元素...');
        } else if (state.scanStatus === 'idle') {
            addSystemMessage('正在初始化知识库...');
            // Trigger scan if not started
            setTimeout(scanAndUploadDOM, 500);
        }
    }

    // ── Dialog Events ────────────────────────────────────
    function setupDialogEvents(dialog) {
        const closeBtn = dialog.querySelector('.voltaire-close');
        const sendBtn = dialog.querySelector('.voltaire-send');
        const input = dialog.querySelector('.voltaire-input');

        closeBtn.addEventListener('click', () => { dialog.classList.remove('active'); state.dialogVisible = false; });
        sendBtn.addEventListener('click', () => sendMessage(input, sendBtn));
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(input, sendBtn); }
        });
        // Suggestion chip clicks
        const suggestions = dialog.querySelector('.voltaire-suggestions');
        suggestions.addEventListener('click', (e) => {
            const chip = e.target.closest('.voltaire-suggestion-chip');
            if (!chip) return;
            const question = chip.dataset.question;
            if (question) {
                input.value = question;
                sendMessage(input, sendBtn);
            }
        });

        // Auto-resize input
        input.addEventListener('input', () => {
            input.style.height = 'auto';
            input.style.height = Math.min(input.scrollHeight, 80) + 'px';
        });
    }

    // ── Send Message ─────────────────────────────────────
    function sendMessage(input, sendBtn) {
        const text = input.value.trim();
        if (!text || state.executing) return;

        sendBtn.disabled = true;
        state.executing = true;

        // Add user message
        addMessage('user', text);
        input.value = '';
        input.style.height = 'auto';

        // Show typing indicator with progress text
        const typingId = showTyping();
        const messagesDiv = document.getElementById('voltaire-messages');

        // Try SSE first, fallback to POST
        trySSE(text, typingId, sendBtn, messagesDiv)
            .catch(function() {
                return fallbackPost(text, typingId, sendBtn, messagesDiv);
            })
            .catch(function(err) {
                removeTyping(typingId);
                addMessage('ai', 'Error: ' + err.message);
                console.error('VoltaireAI Error:', err);
            })
            .finally(function() {
                sendBtn.disabled = false;
                state.executing = false;
                input.focus();
            });
    }

    // ── SSE Streaming ─────────────────────────────────────
    function trySSE(text, typingId, sendBtn, messagesDiv) {
        return new Promise(function(resolve, reject) {
            var url = BASE_URL + '/VoltaireAI/chat/stream?' +
                'message=' + encodeURIComponent(text) +
                '&site_id=' + encodeURIComponent(state.siteId);

            var es = new EventSource(url);
            var timeoutId = setTimeout(function() {
                es.close();
                reject(new Error('SSE timeout'));
            }, 15000); // 15s timeout for connection

            es.addEventListener('message', function(e) {
                try {
                    var event = JSON.parse(e.data);

                    if (event.type === 'progress') {
                        // Update typing indicator text
                        updateTypingText(typingId, event.message || '');
                    } else if (event.type === 'complete') {
                        clearTimeout(timeoutId);
                        es.close();
                        removeTyping(typingId);

                        var data = event.data;
                        state.checklist = data.checklist || null;

                        // Render AI message with markdown
                        addMessage('ai', data.message || data.response || 'No response');

                        // Handle checklist display
                        if (data.checklist) renderChecklist(messagesDiv, data.checklist);

                        // Handle code execution
                        if (data.code && (data.code.indexOf('<js-start>') !== -1 || data.code.indexOf('```js-start') !== -1)) {
                            renderCodeBlock(messagesDiv, data.code, text);
                        }

                        resolve();
                    } else if (event.type === 'error') {
                        clearTimeout(timeoutId);
                        es.close();
                        reject(new Error(event.message || 'SSE error'));
                    }
                } catch (parseErr) {
                    clearTimeout(timeoutId);
                    es.close();
                    reject(parseErr);
                }
            });

            es.addEventListener('error', function() {
                clearTimeout(timeoutId);
                es.close();
                reject(new Error('EventSource connection failed'));
            });
        });
    }

    // ── Fallback POST ─────────────────────────────────────
    function fallbackPost(text, typingId, sendBtn, messagesDiv) {
        return fetch(BASE_URL + '/VoltaireAI/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text, site_id: state.siteId })
        })
        .then(function(res) {
            if (!res.ok) throw new Error('HTTP ' + res.status);
            return res.json();
        })
        .then(function(data) {
            removeTyping(typingId);
            state.checklist = data.checklist || null;

            addMessage('ai', data.message || data.response || 'No response');

            if (data.checklist) renderChecklist(messagesDiv, data.checklist);

            if (data.code && (data.code.indexOf('<js-start>') !== -1 || data.code.indexOf('```js-start') !== -1)) {
                renderCodeBlock(messagesDiv, data.code, text);
            }
        });
    }

    // ── Update typing text ────────────────────────────────
    function updateTypingText(typingId, text) {
        var el = document.getElementById(typingId);
        if (!el) return;

        // Replace the bouncing dots with text + dots
        var content = el.querySelector('.voltaire-content') || el.querySelector('.voltaire-typing');
        if (content) {
            content.className = 'voltaire-content';
            content.style.cssText = 'background:white;padding:10px 14px;border-radius:14px;border-bottom-left-radius:4px;font-size:14px;color:#666;';
            content.innerHTML = text + ' <span style="display:inline-flex;gap:3px;">' +
                '<span style="animation:voltaire-bounce 1.4s infinite ease-in-out both;animation-delay:-0.32s;width:6px;height:6px;background:#999;border-radius:50%;display:inline-block;"></span>' +
                '<span style="animation:voltaire-bounce 1.4s infinite ease-in-out both;animation-delay:-0.16s;width:6px;height:6px;background:#999;border-radius:50%;display:inline-block;"></span>' +
                '<span style="animation:voltaire-bounce 1.4s infinite ease-in-out both;animation-delay:0s;width:6px;height:6px;background:#999;border-radius:50%;display:inline-block;"></span>' +
                '</span>';
        }

        var container = document.getElementById('voltaire-messages');
        if (container) container.scrollTop = container.scrollHeight;
    }

    // ── Messages ─────────────────────────────────────────
    function addMessage(role, text) {
        const container = document.getElementById('voltaire-messages');
        const div = document.createElement('div');
        div.className = 'voltaire-message ' + role;

        const content = document.createElement('div');
        content.className = 'voltaire-content';

        if (role === 'ai' && typeof window.marked !== 'undefined') {
            try {
                // Sanitize: marked's default is safeHTML=false, ensure no scripts
                content.innerHTML = window.marked.parse(text, { breaks: true });
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

    function addSystemMessage(text, onClick) {
        const container = document.getElementById('voltaire-messages');
        const div = document.createElement('div');
        div.className = 'voltaire-message ai';

        const content = document.createElement('div');
        content.className = 'voltaire-content';
        content.style.cssText = 'background:#f0f7ff;color:#555;font-size:13px;padding:8px 14px;border-radius:8px;border-bottom-left-radius:4px;text-align:center;';
        content.textContent = text;

        if (onClick) {
            content.style.cssText += 'cursor:pointer;color:#0066cc;font-weight:600;';
            content.title = '点击重试';
            content.addEventListener('click', onClick);
        }

        div.appendChild(content);
        container.appendChild(div);
        container.scrollTop = container.scrollHeight;
    }

    function showTyping() {
        const container = document.getElementById('voltaire-messages');
        const typing = document.createElement('div');
        const id = 'typing-' + Date.now();
        typing.id = id;
        typing.className = 'voltaire-message ai';
        typing.innerHTML = '<div class="voltaire-typing"><span></span><span></span><span></span></div>';
        container.appendChild(typing);
        container.scrollTop = container.scrollHeight;
        return id;
    }

    function removeTyping(id) {
        const el = document.getElementById(id);
        if (el) el.remove();
    }

    // ── Checklist Rendering ──────────────────────────────
    function renderChecklist(container, checklist) {
        const div = document.createElement('div');
        div.className = 'voltaire-message ai';
        div.id = 'voltaire-checklist-' + Date.now();

        const content = document.createElement('div');
        content.className = 'voltaire-content';

        let html = '<ul class="voltaire-checklist">';
        (checklist.plan || []).forEach(function(item) {
            var status = item.status || 'pending';
            var cls = 'voltaire-checklist-item';
            var icon = '○';
            if (status === 'completed') { cls += ' done'; icon = '✓'; }
            else if (status === 'failed') { cls += ' failed'; icon = '✗'; }
            else if (status === 'in_progress') { cls += ' active'; icon = '◉'; }

            html += '<li class="' + cls + '">';
            html += '<span class="check-icon">' + icon + '</span>';
            html += '<div><span class="step-label">Step ' + item.step + '</span>';
            html += '<strong>' + escapeHtml(item.description || '') + '</strong>';
            if (item.target_element) html += '<br><small>Target: ' + escapeHtml(item.target_element) + '</small>';
            html += '</div></li>';
        });
        html += '</ul>';
        content.innerHTML = html;
        div.appendChild(content);
        container.appendChild(div);
        container.scrollTop = container.scrollHeight;
    }

    // ── Code Execution ───────────────────────────────────
    function extractJS(code) {
        // Strategy 1: new format ```js-start...```js-end (markdown fence)
        var match = code.match(/```js-start\s*\n([\s\S]*?)```js-end/i);
        if (match && match[1]) return match[1].trim();

        // Strategy 2: old format <js-start>...<js-end> or </js-end> (backward compat)
        match = code.match(/<js-start>([\s\S]*?)(?:<\/js-end>|<js-end>)/i);
        if (match && match[1]) return match[1].trim();

        // Strategy 3: strip tags manually (both old and new)
        var stripped = code
            .replace(/```js-start\s*\n?/gi, '')
            .replace(/\n?```js-end/gi, '')
            .replace(/<js-start>/gi, '')
            .replace(/<\/?js-end>/gi, '')
            .trim();
        if (stripped) return stripped;

        // Strategy 4: return as-is (last resort)
        return code.trim();
    }

    function parseCodeSteps(code) {
        // Extract all code blocks (new markdown fence format + old format for backward compat)
        var blocks = [];
        // New format: ```js-start ... ```js-end
        var regexNew = /```js-start\s*\n([\s\S]*?)```js-end/gi;
        // Old format: <js-start> ... <js-end>
        var regexOld = /<js-start>([\s\S]*?)<js-end>/gi;
        var match;

        while ((match = regexNew.exec(code)) !== null) {
            blocks.push({
                jsCode: match[1].trim(),
                startIndex: match.index,
                endIndex: match.index + match[0].length
            });
        }

        while ((match = regexOld.exec(code)) !== null) {
            blocks.push({
                jsCode: match[1].trim(),
                startIndex: match.index,
                endIndex: match.index + match[0].length
            });
        }

        if (blocks.length === 0) return [];

        // Pair each block with its preceding description text
        var steps = [];
        for (var i = 0; i < blocks.length; i++) {
            var descStart = (i === 0) ? 0 : blocks[i - 1].endIndex;
            var descEnd = blocks[i].startIndex;
            var description = code.substring(descStart, descEnd).trim();

            steps.push({
                step: i + 1,
                description: description,
                jsCode: blocks[i].jsCode
            });
        }

        return steps;
    }

    function renderCodeBlock(container, code, originalRequest) {
        var steps = parseCodeSteps(code);

        if (steps.length > 1) {
            renderMultiStepCode(container, steps, originalRequest);
        } else {
            renderSingleCodeBlock(container, extractJS(code), originalRequest);
        }
    }

    function renderSingleCodeBlock(container, jsCode, originalRequest) {
        var div = document.createElement('div');
        div.className = 'voltaire-message ai';
        div.id = 'voltaire-exec-' + Date.now();

        var content = document.createElement('div');
        content.className = 'voltaire-content';

        // Code preview (truncated)
        var pre = document.createElement('pre');
        pre.style.cssText = 'background:#1e1e2e;color:#cdd6f4;padding:12px;border-radius:8px;font-size:12px;overflow-x:auto;';
        pre.textContent = jsCode.length > 300 ? jsCode.substring(0, 300) + '\n// ...' : jsCode;
        pre.id = 'code-pre-' + div.id;
        content.appendChild(pre);

        // Toggle full code button
        var toggleBtn = document.createElement('button');
        toggleBtn.className = 'voltaire-exec-btn';
        toggleBtn.style.cssText = 'margin-right:6px;font-size:11px;padding:3px 10px;background:#666;';
        toggleBtn.textContent = '查看完整代码';
        toggleBtn.addEventListener('click', function() {
            var p = document.getElementById('code-pre-' + div.id);
            if (toggleBtn.textContent === '查看完整代码') {
                p.textContent = jsCode;
                toggleBtn.textContent = '收起代码';
            } else {
                p.textContent = jsCode.length > 300 ? jsCode.substring(0, 300) + '\n// ...' : jsCode;
                toggleBtn.textContent = '查看完整代码';
            }
        });
        content.appendChild(toggleBtn);

        // Execute button
        var btn = document.createElement('button');
        btn.className = 'voltaire-exec-btn warning';
        btn.textContent = '▶ Execute Code';
        btn.addEventListener('click', function() {
            executeJS(jsCode, btn, originalRequest);
        });
        content.appendChild(btn);

        div.appendChild(content);
        container.appendChild(div);
        container.scrollTop = container.scrollHeight;
    }

    function renderMultiStepCode(container, steps, originalRequest) {
        var div = document.createElement('div');
        div.className = 'voltaire-message ai';
        div.id = 'voltaire-exec-' + Date.now();

        var content = document.createElement('div');
        content.className = 'voltaire-content';

        // Execute All button at top
        var allBtn = document.createElement('button');
        allBtn.className = 'voltaire-exec-btn';
        allBtn.textContent = '▶ Execute All Steps';
        allBtn.style.cssText = 'margin-bottom:12px;width:100%;';
        allBtn.addEventListener('click', function() {
            executeAllSteps(steps, allBtn, originalRequest);
        });
        content.appendChild(allBtn);

        // Render each step
        steps.forEach(function(step) {
            var stepDiv = document.createElement('div');
            stepDiv.style.cssText = 'margin:12px 0;padding:10px;background:#fafafa;border-radius:8px;border:1px solid #eee;';
            stepDiv.id = 'step-' + step.step + '-' + Date.now();

            // Step header
            var header = document.createElement('div');
            header.style.cssText = 'font-weight:600;font-size:13px;color:#333;margin-bottom:6px;';
            header.textContent = 'Step ' + step.step;
            stepDiv.appendChild(header);

            // Step description (rendered as markdown or plain text)
            if (step.description) {
                var desc = document.createElement('div');
                desc.style.cssText = 'font-size:13px;color:#555;margin-bottom:8px;line-height:1.5;';
                if (typeof window.marked !== 'undefined') {
                    try {
                        desc.innerHTML = window.marked.parse(step.description, { breaks: true });
                    } catch (e) {
                        desc.textContent = step.description;
                    }
                } else {
                    desc.textContent = step.description;
                }
                stepDiv.appendChild(desc);
            }

            // Code preview
            var pre = document.createElement('pre');
            pre.style.cssText = 'background:#1e1e2e;color:#cdd6f4;padding:10px;border-radius:6px;font-size:11px;overflow-x:auto;max-height:150px;overflow-y:auto;';
            pre.textContent = step.jsCode.length > 200 ? step.jsCode.substring(0, 200) + '\n// ...' : step.jsCode;
            var preId = 'code-pre-' + stepDiv.id;
            pre.id = preId;
            stepDiv.appendChild(pre);

            // Toggle full code
            var toggleBtn = document.createElement('button');
            toggleBtn.className = 'voltaire-exec-btn';
            toggleBtn.style.cssText = 'margin-right:6px;margin-top:4px;font-size:10px;padding:2px 8px;background:#666;';
            toggleBtn.textContent = '查看完整代码';
            toggleBtn.addEventListener('click', function() {
                var p = document.getElementById(preId);
                if (toggleBtn.textContent === '查看完整代码') {
                    p.textContent = step.jsCode;
                    p.style.maxHeight = 'none';
                    toggleBtn.textContent = '收起代码';
                } else {
                    p.textContent = step.jsCode.length > 200 ? step.jsCode.substring(0, 200) + '\n// ...' : step.jsCode;
                    p.style.maxHeight = '150px';
                    toggleBtn.textContent = '查看完整代码';
                }
            });
            stepDiv.appendChild(toggleBtn);

            // Execute button for this step
            var btn = document.createElement('button');
            btn.className = 'voltaire-exec-btn warning';
            btn.style.cssText = 'margin-top:6px;font-size:12px;padding:4px 12px;';
            btn.textContent = '▶ Run Step ' + step.step;
            btn.addEventListener('click', function() {
                executeJS(step.jsCode, btn, originalRequest);
            });
            stepDiv.appendChild(btn);

            content.appendChild(stepDiv);
        });

        div.appendChild(content);
        container.appendChild(div);
        container.scrollTop = container.scrollHeight;
    }

    function executeAllSteps(steps, allBtn, originalRequest) {
        allBtn.disabled = true;
        allBtn.textContent = '⏳ Executing all steps...';

        var successCount = 0;
        var failCount = 0;

        function runNext(index) {
            if (index >= steps.length) {
                allBtn.textContent = '✓ All Done (' + successCount + '/' + steps.length + ' OK)';
                allBtn.className = 'voltaire-exec-btn';
                allBtn.disabled = false;
                return;
            }

            var step = steps[index];
            allBtn.textContent = '⏳ Step ' + step.step + '/' + steps.length + '...';

            try {
                var tl = getTLGlobals();
                var fn = new Function('console', 'screen', 'fireEvent', 'waitFor', 'within', step.jsCode);
                var result = fn(console, tl.screen, tl.fireEvent, tl.waitFor, tl.within);

                var handleResult = function(val) {
                    successCount++;
                    runNext(index + 1);
                };
                var handleError = function(err) {
                    failCount++;
                    console.error('Step ' + step.step + ' failed:', err);
                    runNext(index + 1); // Continue despite error
                };

                if (result && typeof result.then === 'function') {
                    result.then(handleResult).catch(handleError);
                } else {
                    handleResult(result);
                }
            } catch (error) {
                failCount++;
                console.error('Step ' + step.step + ' failed:', error);
                runNext(index + 1);
            }
        }

        runNext(0);
    }

    function getTLGlobals() {
        var tl = window.TestingLibraryDom;
        if (tl) {
            return {
                screen: tl.screen,
                fireEvent: tl.fireEvent,
                waitFor: tl.waitFor,
                within: tl.within
            };
        }
        return {};
    }

    function executeJS(jsCode, btn, originalRequest) {
        var origText = btn.textContent;
        var origClass = btn.className;
        btn.disabled = true;
        btn.textContent = '⏳ Executing...';
        btn.className = 'voltaire-exec-btn';

        function restoreBtn() {
            btn.disabled = false;
            btn.textContent = origText;
            btn.className = origClass;
        }

        // Status badge
        var badge = document.createElement('div');
        badge.className = 'voltaire-exec-badge running';
        badge.textContent = '⏳ Running...';
        btn.parentNode.appendChild(badge);

        try {
            // Execute with testing-library globals available
            var tl = getTLGlobals();
            var fn = new Function('console', 'screen', 'fireEvent', 'waitFor', 'within', jsCode);
            var result = fn(console, tl.screen, tl.fireEvent, tl.waitFor, tl.within);

            // Handle promises
            if (result && typeof result.then === 'function') {
                result
                    .then(function(val) {
                        badge.className = 'voltaire-exec-badge success';
                        badge.textContent = '✓ Executed successfully';
                        restoreBtn();
                        sendFeedback('success', 'Execution completed', originalRequest);
                    })
                    .catch(function(err) {
                        badge.className = 'voltaire-exec-badge failed';
                        badge.textContent = '✗ Failed: ' + (err.message || err);
                        restoreBtn();
                        sendFeedback('failed', err.message || String(err), originalRequest);
                    });
            } else {
                badge.className = 'voltaire-exec-badge success';
                badge.textContent = '✓ Executed successfully';
                restoreBtn();
                sendFeedback('success', 'Execution completed', originalRequest);
            }
        } catch (error) {
            badge.className = 'voltaire-exec-badge failed';
            badge.textContent = '✗ Failed: ' + error.message;
            restoreBtn();
            sendFeedback('failed', error.message, originalRequest);
        }
    }

    function sendFeedback(status, message, originalRequest) {
        fetch(BASE_URL + '/VoltaireAI/execution-feedback', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                status: status,
                message: message,
                original_request: originalRequest,
                site_id: state.siteId
            })
        }).catch(function(err) {
            console.warn('VoltaireAI: Feedback send failed', err);
        });
    }

    // ── Drag ─────────────────────────────────────────────
    function setupDraggable(element, options) {
        let isDragging = false, hasMoved = false;
        let startX, startY, initialX, initialY;
        var target = options.target || element;

        element.addEventListener('mousedown', function(e) {
            isDragging = true;
            hasMoved = false;
            startX = e.clientX;
            startY = e.clientY;
            var rect = target.getBoundingClientRect();
            initialX = rect.left;
            initialY = rect.top;
            if (options.onDragStart) options.onDragStart();
            e.preventDefault();
        });

        document.addEventListener('mousemove', function(e) {
            if (!isDragging) return;
            var dx = e.clientX - startX, dy = e.clientY - startY;
            if (Math.abs(dx) > 5 || Math.abs(dy) > 5) hasMoved = true;
            if (!hasMoved) return;
            var newX = initialX + dx, newY = initialY + dy;
            var maxX = window.innerWidth - target.offsetWidth, maxY = window.innerHeight - target.offsetHeight;
            target.style.left = Math.max(0, Math.min(newX, maxX)) + 'px';
            target.style.top = Math.max(0, Math.min(newY, maxY)) + 'px';
            target.style.bottom = 'auto';
            target.style.right = 'auto';
        });

        document.addEventListener('mouseup', function() {
            if (isDragging) {
                if (options.onDragEnd) options.onDragEnd();
                if (hasMoved && element.id === 'voltaire-floating-btn') {
                    element.dataset.preventClick = 'true';
                    setTimeout(function() { element.dataset.preventClick = 'false'; }, 100);
                }
            }
            isDragging = false;
            hasMoved = false;
        });
    }

    // ── Utilities ────────────────────────────────────────
    function escapeHtml(str) {
        var div = document.createElement('div');
        div.appendChild(document.createTextNode(str));
        return div.innerHTML;
    }

    // ── Click prevention after drag ──────────────────────
    document.addEventListener('click', function(e) {
        var btn = document.getElementById('voltaire-floating-btn');
        if (btn && btn.contains(e.target) && btn.dataset.preventClick === 'true') {
            e.stopImmediatePropagation();
        }
    }, true);

    // ── Init ─────────────────────────────────────────────
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // ── Global API ───────────────────────────────────────
    window.VoltaireAI = {
        toggle: toggleDialog,
        sendMessage: function(msg) {
            var input = document.querySelector('.voltaire-input');
            var sendBtn = document.querySelector('.voltaire-send');
            if (msg && typeof msg === 'string') input.value = msg;
            sendMessage(input, sendBtn);
        },
        setSiteId: function(id) { state.siteId = id; },
        getState: function() { return Object.assign({}, state, { messages: state.messages.slice() }); },
        scanDOM: scanAndUploadDOM
    };
})();