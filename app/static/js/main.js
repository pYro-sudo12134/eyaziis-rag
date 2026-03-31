// Точка входа

document.addEventListener('DOMContentLoaded', () => {
    loadSupportedFormats();
    loadDomain();
    loadStats();
    loadFullHelp();
    document.getElementById('fileInput').addEventListener('change', previewFile);
});

async function loadSupportedFormats() {
    try {
        const response = await fetch('/api/supported_formats');
        const data = await response.json();
        const formatsDiv = document.getElementById('supportedFormats');
        if (data.formats) {
            formatsDiv.innerHTML = data.formats.map(f => `• ${f.toUpperCase()}`).join('<br>');
        }
    } catch (error) {
        document.getElementById('supportedFormats').innerHTML = 'Ошибка загрузки';
    }
}

async function loadDomain() {
    try {
        const response = await fetch('/api/domain');
        const data = await response.json();
        if (data.current_domain) document.getElementById('domainSelect').value = data.current_domain;
        if (data.examples) updateExamples(data.examples);
        if (data.description) document.getElementById('domainDescription').innerHTML = data.description;
    } catch (error) {
        console.error('Error loading domain:', error);
    }
}

async function changeDomain() {
    const domain = document.getElementById('domainSelect').value;
    try {
        const response = await fetch('/api/domain', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ domain })
        });
        const data = await response.json();
        if (data.examples) updateExamples(data.examples);
        if (data.description) document.getElementById('domainDescription').innerHTML = data.description;
        showStatus('uploadStatus', `Предметная область изменена на "${domain}"`, 'success');
        setTimeout(() => {
            const statusDiv = document.getElementById('uploadStatus');
            if (statusDiv) statusDiv.innerHTML = '';
        }, 3000);
    } catch (error) {
        console.error('Error changing domain:', error);
    }
}

async function loadStats() {
    try {
        const response = await fetch('/api/stats');
        const data = await response.json();
        const statsDiv = document.getElementById('statsInfo');
        if (data.vector_store) {
            statsDiv.innerHTML = `
                Документов: ${data.vector_store.doc_count || 0}<br>
                Размер БД: ${((data.vector_store.size_bytes || 0) / 1024).toFixed(1)} KB<br>
                Модель: ${data.config?.embedding_model || 'N/A'}<br>
                LLM: ${data.config?.llm_model || 'N/A'}
            `;
        } else {
            statsDiv.innerHTML = 'Статистика недоступна';
        }
    } catch (error) {
        console.error('Error loading stats:', error);
        document.getElementById('statsInfo').innerHTML = 'Ошибка загрузки статистики';
    }
}

async function uploadDocument() {
    const fileInput = document.getElementById('fileInput');
    const file = fileInput.files[0];
    if (!file) {
        showStatus('uploadStatus', 'Пожалуйста, выберите файл', 'error');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', file);
    
    showStatus('uploadStatus', 'Загрузка и индексация документа...', 'info');
    
    try {
        const response = await fetch('/api/upload', { method: 'POST', body: formData });
        const data = await response.json();
        
        if (data.success) {
            showStatus('uploadStatus', `Документ успешно загружен! Статистика: ${data.statistics.word_count} слов, разбит на ${data.chunks} фрагментов`, 'success');
            addMessage('assistant', `Документ "${file.name}" загружен и проиндексирован.\n\nСодержит ${data.statistics.word_count} слов, разбит на ${data.chunks} фрагментов для поиска.`);
            fileInput.value = '';
            document.getElementById('uploadPreview').style.display = 'none';
            loadStats();
        } else {
            showStatus('uploadStatus', `Ошибка: ${data.error}`, 'error');
        }
    } catch (error) {
        showStatus('uploadStatus', `Ошибка: ${error.message}`, 'error');
    }
}

setInterval(() => {
    loadStats();
}, 30000);