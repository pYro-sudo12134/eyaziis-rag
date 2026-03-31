// Управление сообщениями
let messagesList = [];

function addMessage(role, content, messageIndex = null, syntaxTree = null, semanticAnalysis = null, isEdited = false) {
    const messagesDiv = document.getElementById('messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    
    const actualIndex = messageIndex !== null ? messageIndex : messagesList.length;
    
    let contentHtml = `<div class="message-content" data-message-index="${actualIndex}">${formatMessage(content)}`;
    if (isEdited) contentHtml += `<span class="message-edited-badge">(отредактировано)</span>`;
    contentHtml += `</div>`;
    contentHtml += `<div class="message-actions" id="actions-${actualIndex}"></div>`;
    
    messageDiv.innerHTML = contentHtml;
    messagesDiv.appendChild(messageDiv);
    
    const actionsDiv = messageDiv.querySelector('.message-actions');
    addMessageActions(actionsDiv, role, actualIndex, syntaxTree, semanticAnalysis);
    
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
    
    messagesList.push({
        role, content, syntaxTree, semanticAnalysis,
        element: messageDiv, index: messagesList.length, isEdited
    });
    
    return actualIndex;
}

function addMessageActions(actionsDiv, role, index, syntaxTree, semanticAnalysis) {
    if (role === 'user') {
        addButton(actionsDiv, 'Редактировать', () => editMessage(index));
        addButton(actionsDiv, 'Удалить', () => deleteMessage(index));
    } else if (role === 'assistant') {
        addButton(actionsDiv, 'Перегенерировать', () => regenerateResponse(index));
        addButton(actionsDiv, 'Редактировать', () => editMessage(index));
        addButton(actionsDiv, 'Удалить', () => deleteMessage(index));
        if (syntaxTree) addButton(actionsDiv, 'Редактировать дерево', () => editSyntaxTree(index));
        if (semanticAnalysis) addButton(actionsDiv, 'Редактировать семантику', () => editSemanticAnalysis(index));
    }
}

function addButton(container, text, onClick) {
    const btn = document.createElement('button');
    btn.textContent = text;
    btn.onclick = onClick;
    container.appendChild(btn);
}

async function editMessage(messageIndex) {
    const message = messagesList[messageIndex];
    if (!message) return;
    
    const contentDiv = message.element.querySelector('.message-content');
    const originalContent = message.content;
    
    const editor = document.createElement('textarea');
    editor.className = 'message-content-editor';
    editor.value = originalContent;
    editor.rows = 3;
    
    const buttonContainer = document.createElement('div');
    buttonContainer.style.marginTop = '8px';
    
    const saveBtn = createButton('Сохранить', '#667eea', async () => {
        const newContent = editor.value.trim();
        if (!newContent) return;
        
        const response = await fetch('/api/update_message', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                session_id: 'web_session',
                message_index: messageIndex,
                content: newContent
            })
        });
        
        const data = await response.json();
        if (data.success) {
            contentDiv.innerHTML = formatMessage(newContent);
            contentDiv.innerHTML += '<span class="message-edited-badge">(отредактировано)</span>';
            message.content = newContent;
            message.isEdited = true;
            
            if (message.role === 'user') {
                const nextAssistant = messagesList.find((msg, idx) => idx > messageIndex && msg.role === 'assistant');
                if (nextAssistant && confirm('Сообщение изменено. Перегенерировать ответ ассистента?')) {
                    const assistantIndex = messagesList.findIndex((msg, idx) => idx > messageIndex && msg.role === 'assistant');
                    if (assistantIndex !== -1) await regenerateResponse(assistantIndex);
                }
            }
            
            await saveHistory();
            contentDiv.classList.remove('editable');
        } else {
            alert('Ошибка сохранения: ' + data.error);
        }
    });
    
    const cancelBtn = createButton('Отмена', '#ccc', () => {
        contentDiv.innerHTML = formatMessage(originalContent);
        if (message.isEdited) contentDiv.innerHTML += '<span class="message-edited-badge">(отредактировано)</span>';
        contentDiv.classList.remove('editable');
    });
    
    buttonContainer.appendChild(saveBtn);
    buttonContainer.appendChild(cancelBtn);
    
    contentDiv.innerHTML = '';
    contentDiv.appendChild(editor);
    contentDiv.appendChild(buttonContainer);
    contentDiv.classList.add('editable');
    editor.focus();
}

function createButton(text, bgColor, onClick) {
    const btn = document.createElement('button');
    btn.textContent = text;
    btn.style.padding = '4px 12px';
    btn.style.marginRight = '8px';
    btn.style.background = bgColor;
    btn.style.color = 'white';
    btn.style.border = 'none';
    btn.style.borderRadius = '4px';
    btn.style.cursor = 'pointer';
    btn.onclick = onClick;
    return btn;
}

async function deleteMessage(messageIndex) {
    if (!confirm('Удалить это сообщение?')) return;
    
    const response = await fetch('/api/delete_message', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ session_id: 'web_session', message_index: messageIndex })
    });
    
    const data = await response.json();
    if (data.success) {
        const message = messagesList[messageIndex];
        if (message && message.element) message.element.remove();
        messagesList.splice(messageIndex, 1);
        
        messagesList.forEach((msg, idx) => {
            msg.index = idx;
            const contentDiv = msg.element.querySelector('.message-content');
            if (contentDiv) contentDiv.setAttribute('data-message-index', idx);
            const actionsDiv = msg.element.querySelector('.message-actions');
            if (actionsDiv) {
                actionsDiv.innerHTML = '';
                addMessageActions(actionsDiv, msg.role, idx, msg.syntaxTree, msg.semanticAnalysis);
            }
        });
        
        await saveHistory();
    } else {
        alert('Ошибка удаления: ' + data.error);
    }
}