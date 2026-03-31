// Вспомогательные функции
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatMessage(content) {
    return content.replace(/\n/g, '<br>');
}

function showStatus(elementId, message, type) {
    const element = document.getElementById(elementId);
    if (!element) return;
    element.innerHTML = `<div class="status-message ${type}">${message}</div>`;
    setTimeout(() => {
        if (document.getElementById(elementId) === element) {
            element.innerHTML = '';
        }
    }, 5000);
}

function addLoadingMessage() {
    const messagesDiv = document.getElementById('messages');
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'message assistant loading-message';
    loadingDiv.id = 'loading-' + Date.now();
    loadingDiv.innerHTML = '<div class="message-content">Думаю...</div>';
    messagesDiv.appendChild(loadingDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
    return loadingDiv.id;
}

function removeLoadingMessage(id) {
    const loadingDiv = document.getElementById(id);
    if (loadingDiv) loadingDiv.remove();
}

function addSources(sources) {
    const messagesDiv = document.getElementById('messages');
    const lastMessage = messagesDiv.lastChild;
    if (lastMessage && lastMessage.classList.contains('assistant')) {
        const sourcesDiv = document.createElement('div');
        sourcesDiv.className = 'sources';
        sourcesDiv.innerHTML = 'Источники: ' + sources.map(s => s.text.substring(0, 50) + '...').join(', ');
        lastMessage.appendChild(sourcesDiv);
    }
}