// UI-компоненты
function switchTab(tabName) {
    const mainTab = document.getElementById('tab-main');
    const helpTab = document.getElementById('tab-help');
    const buttons = document.querySelectorAll('.tab-btn');
    
    buttons.forEach(btn => btn.classList.remove('active'));
    
    if (tabName === 'main') {
        mainTab.classList.add('active');
        mainTab.style.display = 'block';
        helpTab.classList.remove('active');
        helpTab.style.display = 'none';
        document.querySelector('.tabs .tab-btn:first-child').classList.add('active');
    } else {
        helpTab.classList.add('active');
        helpTab.style.display = 'block';
        mainTab.classList.remove('active');
        mainTab.style.display = 'none';
        document.querySelector('.tabs .tab-btn:last-child').classList.add('active');
    }
}

function handleKeyPress(event) {
    if (event.key === 'Enter' && !event.ctrlKey) {
        event.preventDefault();
        if (typeof sendMessage === 'function') sendMessage();
    }
}

function previewFile(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    const previewDiv = document.getElementById('uploadPreview');
    const ext = file.name.split('.').pop().toLowerCase();
    
    previewDiv.style.display = 'block';
    previewDiv.innerHTML = `
        <strong>${file.name}</strong><br>
        Размер: ${(file.size / 1024).toFixed(2)} KB<br>
        Тип: ${ext.toUpperCase()}<br>
        <span style="color: #667eea;">Готов к загрузке</span>
    `;
}

function updateExamples(examples) {
    const list = document.getElementById('examplesList');
    if (!examples || examples.length === 0) {
        list.innerHTML = '<li>Нет примеров</li>';
        return;
    }
    list.innerHTML = examples.map(ex => `<li onclick="setExample('${escapeHtml(ex).replace(/'/g, "\\'")}')">${escapeHtml(ex)}</li>`).join('');
}

function setExample(text) {
    document.getElementById('messageInput').value = text;
    if (typeof sendMessage === 'function') sendMessage();
}