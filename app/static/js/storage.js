// Работа с S3 хранилищем
async function loadResultsList() {
    try {
        const response = await fetch('/api/list_results');
        const data = await response.json();
        
        const listDiv = document.getElementById('resultsList');
        if (data.success && data.results && data.results.length > 0) {
            listDiv.innerHTML = data.results.map(r => `
                <div class="result-item" onclick="loadResult('${r.filename}')">
                    <div class="result-filename">${escapeHtml(r.filename)}</div>
                    <div class="result-date">${new Date(r.modified).toLocaleString()}</div>
                    <div style="font-size: 10px;">${(r.size / 1024).toFixed(1)} KB</div>
                </div>
            `).join('');
        } else {
            listDiv.innerHTML = '<div class="loading">Нет сохраненных результатов</div>';
        }
    } catch (error) {
        document.getElementById('resultsList').innerHTML = `<div class="loading">Ошибка: ${error.message}</div>`;
    }
}

async function loadResult(filename) {
    try {
        const response = await fetch(`/api/load_result/${filename}`);
        const data = await response.json();
        
        currentText = data.text;
        
        if (data.analysis) {
            currentSemanticAnalysis = data.analysis;
            renderSemanticAnalysis(data.analysis);
            
            if (data.analysis.syntax_tree) {
                currentSyntaxTree = data.analysis.syntax_tree;
                renderSyntaxTree(data.analysis.syntax_tree);
            }
            
            addMessage('assistant', `Загружен семантический анализ: ${filename}\n\nИсходный текст: "${data.text}"`);
        }
        else if (data.syntax_tree && data.type !== 'semantic_analysis') {
            currentSyntaxTree = data.syntax_tree;
            renderSyntaxTree(data.syntax_tree);
            addMessage('assistant', `Загружен синтаксический анализ: ${filename}\n\nИсходный текст: "${data.text}"`);
        }
        else if (data.history) {
            addMessage('assistant', `Загружена история: ${filename}`);
        }
        
    } catch (error) {
        alert(`Ошибка загрузки: ${error.message}`);
    }
}

async function deleteResult(filename) {
    if (!confirm(`Удалить файл ${filename}?`)) return;
    
    try {
        const response = await fetch(`/api/delete_result/${filename}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        if (data.success) {
            alert('Файл удален');
            loadResultsList();
        } else {
            alert('Ошибка удаления: ' + data.error);
        }
    } catch (error) {
        alert('Ошибка: ' + error.message);
    }
}