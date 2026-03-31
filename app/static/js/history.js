// Управление историей диалога
async function saveHistory() {
    const history = [];
    for (const msg of messagesList) {
        history.push({
            role: msg.role,
            content: msg.content,
            timestamp: new Date().toISOString(),
            syntax_tree: msg.syntaxTree,
            semantic_analysis: msg.semanticAnalysis,
            edited: msg.isEdited || false
        });
    }
    
    if (history.length === 0) return;
    
    try {
        const response = await fetch('/api/history/web_session', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ history: history })
        });
        
        const data = await response.json();
        if (!data.success) {
            console.error('Failed to save history:', data.error);
        }
    } catch (error) {
        console.error('Error saving history:', error);
    }
}

async function loadHistory() {
    try {
        const response = await fetch('/api/history/web_session');
        const data = await response.json();
        
        if (data.success && data.history && data.history.length > 0) {
            const messagesDiv = document.getElementById('messages');
            messagesDiv.innerHTML = '';
            messagesList = [];
            
            data.history.forEach((msg, idx) => {
                const syntaxTree = msg.syntax_tree || null;
                const semanticAnalysis = msg.semantic_analysis || null;
                const isEdited = msg.edited || false;
                
                addMessage(msg.role, msg.content, idx, syntaxTree, semanticAnalysis, isEdited);
                
                const lastMsg = messagesList[messagesList.length - 1];
                if (lastMsg) {
                    lastMsg.syntaxTree = syntaxTree;
                    lastMsg.semanticAnalysis = semanticAnalysis;
                    lastMsg.isEdited = isEdited;
                }
            });
            
            showStatus('uploadStatus', `Загружено ${data.history.length} сообщений`, 'success');
            
            const lastAssistant = [...data.history].reverse().find(m => m.role === 'assistant');
            if (lastAssistant && lastAssistant.semantic_analysis) {
                currentSemanticAnalysis = lastAssistant.semantic_analysis;
                renderSemanticAnalysis(lastAssistant.semantic_analysis);
            }
            if (lastAssistant && lastAssistant.syntax_tree) {
                currentSyntaxTree = lastAssistant.syntax_tree;
                renderSyntaxTree(lastAssistant.syntax_tree);
            }
        } else {
            showStatus('uploadStatus', 'Нет сохранённой истории', 'error');
        }
    } catch (error) {
        showStatus('uploadStatus', `Ошибка загрузки: ${error.message}`, 'error');
    }
}

async function clearHistory() {
    if (confirm('Очистить историю диалога?')) {
        try {
            await fetch('/api/history/web_session', {method: 'DELETE'});
            document.getElementById('messages').innerHTML = '';
            messagesList = [];
            addMessage('assistant', 'История диалога очищена.');
            showStatus('uploadStatus', 'История очищена', 'success');
            currentSyntaxTree = null;
            currentSemanticAnalysis = null;
            document.getElementById('syntaxTree').innerHTML = '<div class="loading">Отправьте сообщение, чтобы увидеть синтаксическое дерево</div>';
            document.getElementById('semanticAnalysis').innerHTML = '<div class="loading">Отправьте сообщение, чтобы увидеть семантический анализ</div>';
        } catch (error) {
            showStatus('uploadStatus', `Ошибка: ${error.message}`, 'error');
        }
    }
}