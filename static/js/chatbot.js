/* ═══════════════════════════════════════════════════════════════
   CHATBOT.JS — AI Assistant interaction logic
═══════════════════════════════════════════════════════════════ */

'use strict';

/* ── State ───────────────────────────────────────────────────── */
var ChatState = {
  isSending: false,
  messageCount: 0,
};

/* ── DOM references (resolved after DOM ready) ───────────────── */
var DOM = {};

/* ── Initialize ─────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', function () {
  DOM.messages     = document.getElementById('chatMessages');
  DOM.input        = document.getElementById('chatInput');
  DOM.sendBtn      = document.getElementById('chatSendBtn');
  DOM.suggestions  = document.getElementById('chatSuggestions');

  if (!DOM.input) return; // chatbot not on this page

  // Enter key to send
  DOM.input.addEventListener('keydown', function (e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  // Auto-focus input
  setTimeout(function () { DOM.input && DOM.input.focus(); }, 300);
});


/* ══════════════════════════════════════════════════════════════
   PUBLIC: sendMessage (called from onclick)
══════════════════════════════════════════════════════════════ */
function sendMessage() {
  if (!DOM.input) {
    DOM.input = document.getElementById('chatInput');
  }
  var text = DOM.input ? DOM.input.value.trim() : '';
  if (!text || ChatState.isSending) return;

  hideChips();
  appendUserMessage(text);
  DOM.input.value = '';
  showTyping();
  setLoading(true);

  fetch('/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Requested-With': 'XMLHttpRequest'
    },
    body: JSON.stringify({ message: text })
  })
  .then(function (res) {
    if (!res.ok) throw new Error('HTTP ' + res.status);
    return res.json();
  })
  .then(function (data) {
    removeTyping();
    appendBotMessage(data.response || 'Sorry, I could not process that.');
  })
  .catch(function (err) {
    removeTyping();
    appendBotMessage('⚠️ Sorry, I had a connection issue. Please try again.');
    console.warn('Chat error:', err);
  })
  .finally(function () {
    setLoading(false);
    scrollToBottom();
  });
}


/* ══════════════════════════════════════════════════════════════
   PUBLIC: sendSuggestion (called from suggestion chip onclick)
══════════════════════════════════════════════════════════════ */
function sendSuggestion(btn) {
  if (!DOM.input) DOM.input = document.getElementById('chatInput');
  if (DOM.input) DOM.input.value = btn.textContent.trim();
  sendMessage();
}


/* ══════════════════════════════════════════════════════════════
   MESSAGE RENDERING
══════════════════════════════════════════════════════════════ */
function appendUserMessage(text) {
  var msg = buildMsg('user-msg', escapeHtml(text));
  getMessages().appendChild(msg);
  scrollToBottom();
  ChatState.messageCount++;
}

function appendBotMessage(markdown) {
  var html = markdownToHtml(markdown);
  var msg = buildMsg('bot-msg', html);
  getMessages().appendChild(msg);
  scrollToBottom();
  ChatState.messageCount++;
}

function buildMsg(cls, htmlContent) {
  var wrapper = document.createElement('div');
  wrapper.className = 'chat-msg ' + cls;

  var bubble = document.createElement('div');
  bubble.className = 'msg-bubble';
  bubble.innerHTML = htmlContent;

  var time = document.createElement('div');
  time.className = 'msg-time';
  time.textContent = nowTime();

  wrapper.appendChild(bubble);
  wrapper.appendChild(time);
  return wrapper;
}


/* ══════════════════════════════════════════════════════════════
   TYPING INDICATOR
══════════════════════════════════════════════════════════════ */
function showTyping() {
  var msg = document.createElement('div');
  msg.className = 'chat-msg bot-msg typing-indicator';
  msg.id = 'typingIndicator';

  var bubble = document.createElement('div');
  bubble.className = 'msg-bubble';
  bubble.innerHTML = '<div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>';

  msg.appendChild(bubble);
  getMessages().appendChild(msg);
  scrollToBottom();
}

function removeTyping() {
  var el = document.getElementById('typingIndicator');
  if (el) el.remove();
}


/* ══════════════════════════════════════════════════════════════
   MARKDOWN → HTML (minimal parser for chatbot responses)
══════════════════════════════════════════════════════════════ */
function markdownToHtml(text) {
  if (!text) return '';

  // Escape dangerous HTML first
  var safe = escapeHtml(text);

  // **bold**
  safe = safe.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

  // *italic*
  safe = safe.replace(/\*([^*]+)\*/g, '<em>$1</em>');

  // Line breaks
  var lines = safe.split('\n');
  var result = [];
  var inList = false;

  lines.forEach(function(line) {
    var trimmed = line.trim();

    if (trimmed === '') {
      if (inList) { result.push('</ul>'); inList = false; }
      result.push('<br/>');
      return;
    }

    // Bullet list items: "  • item" or "• item"
    if (/^•/.test(trimmed)) {
      if (!inList) { result.push('<ul style="padding-left:16px;margin:6px 0;">'); inList = true; }
      result.push('<li style="margin:3px 0;">' + trimmed.replace(/^•\s*/, '') + '</li>');
      return;
    }

    if (inList) { result.push('</ul>'); inList = false; }
    result.push(trimmed);
  });

  if (inList) result.push('</ul>');

  // Join non-list lines with <br>
  var out = '';
  for (var i = 0; i < result.length; i++) {
    var r = result[i];
    if (r.startsWith('<ul') || r.startsWith('</ul>') || r.startsWith('<li') || r === '<br/>') {
      out += r;
    } else {
      out += r + (i < result.length - 1 ? '<br/>' : '');
    }
  }

  return out;
}


/* ══════════════════════════════════════════════════════════════
   HELPERS
══════════════════════════════════════════════════════════════ */
function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function getMessages() {
  if (!DOM.messages) DOM.messages = document.getElementById('chatMessages');
  return DOM.messages;
}

function scrollToBottom() {
  var msgs = getMessages();
  if (msgs) {
    setTimeout(function() {
      msgs.scrollTop = msgs.scrollHeight;
    }, 50);
  }
}

function hideChips() {
  if (!DOM.suggestions) DOM.suggestions = document.getElementById('chatSuggestions');
  if (DOM.suggestions && ChatState.messageCount > 0) {
    DOM.suggestions.style.display = 'none';
  }
}

function setLoading(state) {
  ChatState.isSending = state;
  var btn = DOM.sendBtn || document.getElementById('chatSendBtn');
  if (btn) btn.disabled = state;
  var input = DOM.input || document.getElementById('chatInput');
  if (input) input.disabled = state;
}

function nowTime() {
  var d = new Date();
  return d.getHours().toString().padStart(2, '0') + ':' + d.getMinutes().toString().padStart(2, '0');
}

/* ══════════════════════════════════════════════════════════════
   TOGGLE CHATBOT WINDOW
 ══════════════════════════════════════════════════════════════ */
function toggleChatbot() {
  var sidebar = document.getElementById('chatbotSidebar');
  if (!sidebar) return;

  sidebar.classList.toggle('active');
  
  // Focus input when opened
  if (sidebar.classList.contains('active')) {
    setTimeout(function() {
      var input = document.getElementById('chatInput');
      if (input) input.focus();
    }, 400);
  }
}
