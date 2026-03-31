// Синтаксическое дерево
let currentSyntaxTree = null;

async function analyzeSyntaxOnly(text) {
    const loadingId = addLoadingMessage();
    try {
        const response = await fetch('/api/syntax', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({text: text})
        });
        const data = await response.json();
        removeLoadingMessage(loadingId);
        
        currentText = text;
        currentSyntaxTree = data;
        renderSyntaxTree(data);
        addMessage('assistant', `Синтаксический анализ текста: "${text}"`);
    } catch (error) {
        removeLoadingMessage(loadingId);
        addMessage('assistant', `Ошибка: ${error.message}`);
    }
}

function renderSyntaxTree(tree) {
    const container = document.getElementById('syntaxTree');
    container.innerHTML = '';
    
    if (!tree) {
        container.innerHTML = '<div class="loading">Не удалось построить дерево</div>';
        return;
    }
    
    let normalizedTree = tree;
    if (tree.word) {
        normalizedTree = { name: tree.word, children: tree.children || [] };
        if (tree.role) normalizedTree.pos = tree.role;
    }
    
    if (!normalizedTree.name && !normalizedTree.word) {
        container.innerHTML = '<div class="loading">Не удалось построить дерево</div>';
        return;
    }
    
    const treeElement = createTreeElement(normalizedTree);
    container.appendChild(treeElement);
}

function createTreeElement(node, level = 0) {
    const div = document.createElement('div');
    div.className = 'tree-node';
    div.style.marginLeft = level * 20 + 'px';
    
    const content = document.createElement('div');
    content.className = 'tree-node-content';
    
    const nameSpan = document.createElement('span');
    nameSpan.className = 'tree-node-name';
    nameSpan.textContent = node.name || node.word || '?';
    content.appendChild(nameSpan);
    
    if (node.pos || node.role) {
        const posSpan = document.createElement('span');
        posSpan.className = 'tree-node-pos';
        posSpan.textContent = `(${node.pos || node.role})`;
        content.appendChild(posSpan);
    }
    
    div.appendChild(content);
    
    if (node.children && node.children.length > 0) {
        node.children.forEach(child => {
            div.appendChild(createTreeElement(child, level + 1));
        });
    }
    
    return div;
}

function editSyntaxTree(messageIndex) {
    const message = messagesList[messageIndex];
    if (!message || !message.syntaxTree) {
        alert('Нет синтаксического дерева для редактирования');
        return;
    }
    
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    
    const editor = document.createElement('div');
    editor.className = 'syntax-tree-editor';
    editor.innerHTML = `
        <h3 style="margin-bottom: 12px;">Редактирование синтаксического дерева</h3>
        <textarea id="tree-editor-textarea" style="width:100%; min-height:300px; font-family:monospace; font-size:12px; padding:10px; border:1px solid #ddd; border-radius:8px;">${JSON.stringify(message.syntaxTree, null, 2)}</textarea>
        <div style="margin-top: 12px;">
            <button id="save-tree-btn" style="padding: 8px 16px; background: #667eea; color: white; border: none; border-radius: 6px; cursor: pointer;">Сохранить</button>
            <button id="cancel-tree-btn" style="padding: 8px 16px; margin-left: 8px; background: #ccc; border: none; border-radius: 6px; cursor: pointer;">Отмена</button>
        </div>
        <div style="margin-top: 12px; font-size: 12px; color: #666;">
            <strong>Формат JSON:</strong><br>
            {
                "word": "главное_слово",
                "role": "сказуемое",
                "children": [
                    {"word": "зависимое", "role": "подлежащее", "children": []}
                ]
            }
        </div>
    `;
    
    document.body.appendChild(overlay);
    document.body.appendChild(editor);
    
    const textarea = editor.querySelector('#tree-editor-textarea');
    
    editor.querySelector('#save-tree-btn').onclick = async () => {
        try {
            const updatedTree = JSON.parse(textarea.value);
            
            const response = await fetch('/api/update_syntax_tree', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    session_id: 'web_session',
                    message_index: messageIndex,
                    syntax_tree: updatedTree
                })
            });
            
            const data = await response.json();
            if (data.success) {
                message.syntaxTree = updatedTree;
                currentSyntaxTree = updatedTree;
                renderSyntaxTree(updatedTree);
                alert('Синтаксическое дерево обновлено');
                editor.remove();
                overlay.remove();
                await saveHistory();
            } else {
                alert('Ошибка: ' + data.error);
            }
        } catch (e) {
            alert('Ошибка парсинга JSON: ' + e.message);
        }
    };
    
    editor.querySelector('#cancel-tree-btn').onclick = () => {
        editor.remove();
        overlay.remove();
    };
}

async function saveSyntaxTree() {
    if (!currentSyntaxTree) {
        alert('Нет синтаксического дерева для сохранения');
        return;
    }
    
    try {
        const response = await fetch('/api/save_result', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                text: currentText,
                syntax_tree: currentSyntaxTree,
                type: 'syntax',
                metadata: {
                    timestamp: new Date().toISOString(),
                    domain: document.getElementById('domainSelect').value
                }
            })
        });
        
        const data = await response.json();
        if (data.success) {
            alert(`Результат сохранен как ${data.filename}`);
            if (typeof loadResultsList === 'function') loadResultsList();
        } else {
            alert(`Ошибка: ${data.error}`);
        }
    } catch (error) {
        alert(`Ошибка: ${error.message}`);
    }
}