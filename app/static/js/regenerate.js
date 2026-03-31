// Перегенерация ответов
async function regenerateResponse(messageIndex) {
    if (!confirm('Перегенерировать ответ?')) return;
    
    const message = messagesList[messageIndex];
    if (!message || message.role !== 'assistant') {
        alert('Можно перегенерировать только ответ ассистента');
        return;
    }
    
    let userMessage = null;
    for (let i = messageIndex - 1; i >= 0; i--) {
        if (messagesList[i].role === 'user') {
            userMessage = messagesList[i].content;
            break;
        }
    }
    
    if (!userMessage) {
        alert('Не найден вопрос пользователя для перегенерации');
        return;
    }
    
    try {
        const response = await fetch('/api/regenerate_response', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                session_id: 'web_session',
                message_index: messageIndex
            })
        });
        
        const data = await response.json();
        if (data.success) {
            const contentDiv = message.element.querySelector('.message-content');
            contentDiv.innerHTML = formatMessage(data.new_content) + '<span class="message-edited-badge">(перегенерировано)</span>';
            message.content = data.new_content;
            message.syntaxTree = data.syntax_tree;
            
            if (data.syntax_tree) {
                currentSyntaxTree = data.syntax_tree;
                renderSyntaxTree(data.syntax_tree);
            }
            
            try {
                const semanticResponse = await fetch('/api/semantic_analysis', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({text: userMessage})
                });
                const semanticData = await semanticResponse.json();
                if (semanticData.success && semanticData.analysis) {
                    currentSemanticAnalysis = semanticData.analysis;
                    renderSemanticAnalysis(semanticData.analysis);
                    message.semanticAnalysis = semanticData.analysis;
                }
            } catch (semanticError) {
                console.error('Error getting semantic analysis:', semanticError);
            }
            
            await saveHistory();
            
            const actionsDiv = message.element.querySelector('.message-actions');
            if (actionsDiv && message.semanticAnalysis && !actionsDiv.innerHTML.includes('Редактировать семантику')) {
                const editSemanticBtn = document.createElement('button');
                editSemanticBtn.textContent = 'Редактировать семантику';
                editSemanticBtn.onclick = () => editSemanticAnalysis(messageIndex);
                actionsDiv.appendChild(editSemanticBtn);
            }
        } else {
            alert('Ошибка: ' + data.error);
        }
    } catch (error) {
        alert('Ошибка: ' + error.message);
    }
}