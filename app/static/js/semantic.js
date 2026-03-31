// Семантический анализ
let currentSemanticAnalysis = null;
let currentText = '';

async function analyzeSemanticOnly(text) {
    const loadingId = addLoadingMessage();
    try {
        const response = await fetch('/api/semantic_analysis', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ text })
        });
        const data = await response.json();
        removeLoadingMessage(loadingId);
        
        if (data.success && data.analysis) {
            currentText = text;
            currentSemanticAnalysis = data.analysis;
            renderSemanticAnalysis(data.analysis);
            addMessage('assistant', `Семантический анализ текста: "${text}"`);
        } else {
            addMessage('assistant', 'Не удалось выполнить семантический анализ');
        }
    } catch (error) {
        removeLoadingMessage(loadingId);
        addMessage('assistant', `Ошибка: ${error.message}`);
    }
}

function renderSemanticAnalysis(analysis) {
    const container = document.getElementById('semanticAnalysis');
    if (!container) return;
    container.innerHTML = '';
    
    if (!analysis) {
        container.innerHTML = '<div class="loading">Не удалось выполнить семантический анализ</div>';
        return;
    }
    
    if (analysis.semantic_roles && analysis.semantic_roles.length > 0) {
        const rolesSection = createSection('Семантические роли (актанты)');
        analysis.semantic_roles.forEach(role => {
            const roleDiv = createRoleCard(role);
            rolesSection.appendChild(roleDiv);
        });
        container.appendChild(rolesSection);
    }
    
    if (analysis.semantic_relations && analysis.semantic_relations.length > 0) {
        const relationsSection = createSection('Семантические отношения');
        analysis.semantic_relations.forEach(rel => {
            const relDiv = createRelationCard(rel);
            relationsSection.appendChild(relDiv);
        });
        container.appendChild(relationsSection);
    }
    
    if (analysis.valency_frame) {
        const valencySection = createSection('Валентностная рамка');
        valencySection.appendChild(createValencyCard(analysis.valency_frame));
        container.appendChild(valencySection);
    }
    
    if (analysis.summary) {
        const summarySection = createSection('Сводка');
        summarySection.appendChild(createSummaryCard(analysis.summary));
        container.appendChild(summarySection);
    }
    
    if (container.innerHTML === '') {
        container.innerHTML = '<div class="loading">Нет данных для семантического анализа</div>';
    }
}

function createSection(title) {
    const section = document.createElement('div');
    section.className = 'semantic-section';
    section.innerHTML = `<h4 style="margin: 10px 0 5px 0; color: #764ba2;">${title}</h4>`;
    return section;
}

function createRoleCard(role) {
    const div = document.createElement('div');
    div.className = 'role-card';
    
    let html = `<strong>Предикат:</strong> ${role.predicate || '—'}<br>`;
    
    const fields = [
        { key: 'agent', label: 'Агент (субъект)' },
        { key: 'counter_agent', label: 'Контрагент' },
        { key: 'patient', label: 'Пациенс (объект)' },
        { key: 'content', label: 'Содержание' },
        { key: 'addressee', label: 'Адресат' },
        { key: 'recipient', label: 'Получатель' },
        { key: 'instrument', label: 'Инструмент' },
        { key: 'means', label: 'Средство' },
        { key: 'location', label: 'Локация' },
        { key: 'source', label: 'Начальная точка' },
        { key: 'destination', label: 'Конечная точка' },
        { key: 'route', label: 'Маршрут' },
        { key: 'time', label: 'Время' },
        { key: 'duration', label: 'Срок' },
        { key: 'quantity', label: 'Количество' },
        { key: 'manner', label: 'Способ' },
        { key: 'condition', label: 'Условие' },
        { key: 'motivation', label: 'Мотивировка' },
        { key: 'cause', label: 'Причина' },
        { key: 'result', label: 'Результат' },
        { key: 'purpose', label: 'Цель' },
        { key: 'aspect', label: 'Аспект' },
        { key: 'material', label: 'Материал' },
        { key: 'price', label: 'Цена/вознаграждение' }
    ];
    
    for (const field of fields) {
        if (role[field.key]) html += `<strong>${field.label}:</strong> ${role[field.key]}<br>`;
    }
    
    div.innerHTML = html;
    return div;
}

function createRelationCard(rel) {
    const typeMap = {
        'hypernym': 'Гипероним', 'hyponym': 'Гипоним', 'synonym': 'Синоним',
        'antonym': 'Антоним', 'cause_effect': 'Причина-следствие', 'part_whole': 'Часть-целое'
    };
    const typeLabel = typeMap[rel.type] || rel.type;
    
    const div = document.createElement('div');
    div.style.cssText = 'background: white; padding: 8px; margin: 5px 0; border-radius: 6px; font-size: 13px;';
    div.innerHTML = `<strong>${typeLabel}:</strong> "${rel.word1}" ↔ "${rel.word2}"<br>
                     <span style="font-size: 11px; color: #666;">${rel.explanation || ''}</span>`;
    return div;
}

function createValencyCard(frame) {
    const div = document.createElement('div');
    div.style.cssText = 'background: white; padding: 10px; border-radius: 8px; font-size: 13px;';
    
    let html = `<strong>Предикат:</strong> ${frame.predicate || '—'}<br>`;
    if (frame.required_actants?.length) html += `<strong>Обязательные актанты:</strong> ${frame.required_actants.join(', ')}<br>`;
    if (frame.optional_actants?.length) html += `<strong>Факультативные актанты:</strong> ${frame.optional_actants.join(', ')}<br>`;
    if (frame.total_valencies) html += `<strong>Общее число валентностей:</strong> ${frame.total_valencies}<br>`;
    if (frame.description) html += `<strong>Описание:</strong> ${frame.description}<br>`;
    
    div.innerHTML = html;
    return div;
}

function createSummaryCard(summary) {
    const div = document.createElement('div');
    div.style.cssText = 'background: white; padding: 10px; border-radius: 8px; font-size: 13px;';
    div.innerHTML = `
        <strong>Центральный предикат:</strong> ${summary.predicate_center || '—'}<br>
        <strong>Участники:</strong> ${(summary.participants || []).join(', ') || '—'}<br>
        <strong>Обстоятельства:</strong> ${(summary.circumstances || []).join(', ') || '—'}<br>
        <strong>Сложность:</strong> ${summary.complexity || '—'}<br>
        <strong>Тип:</strong> ${summary.type || '—'}
    `;
    return div;
}

async function saveSemanticAnalysis() {
    if (!currentSemanticAnalysis) {
        alert('Нет данных для сохранения. Сначала отправьте сообщение.');
        return;
    }
    
    const response = await fetch('/api/save_result', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            text: currentText,
            analysis: currentSemanticAnalysis,
            type: 'semantic_analysis',
            metadata: {
                timestamp: new Date().toISOString(),
                domain: document.getElementById('domainSelect').value
            }
        })
    });
    
    const data = await response.json();
    if (data.success) {
        alert(`Семантический анализ сохранен как ${data.filename}`);
        if (typeof loadResultsList === 'function') loadResultsList();
    } else {
        alert(`Ошибка: ${data.error}`);
    }
}

async function editSemanticAnalysis(messageIndex) {
    const message = messagesList[messageIndex];
    if (!message || !message.semanticAnalysis) {
        alert('Нет семантического анализа для редактирования');
        return;
    }
    
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    
    const editor = document.createElement('div');
    editor.className = 'syntax-tree-editor';
    editor.style.maxWidth = '900px';
    editor.innerHTML = `
        <h3 style="margin-bottom: 12px;">Редактирование семантического анализа</h3>
        <textarea id="semantic-editor-textarea" style="width:100%; min-height:400px; font-family:monospace; font-size:12px; padding:10px; border:1px solid #ddd; border-radius:8px;">${JSON.stringify(message.semanticAnalysis, null, 2)}</textarea>
        <div style="margin-top: 12px;">
            <button id="save-semantic-btn" style="padding: 8px 16px; background: #667eea; color: white; border: none; border-radius: 6px; cursor: pointer;">Сохранить</button>
            <button id="cancel-semantic-btn" style="padding: 8px 16px; margin-left: 8px; background: #ccc; border: none; border-radius: 6px; cursor: pointer;">Отмена</button>
        </div>
        <div style="margin-top: 12px; font-size: 12px; color: #666;">
            <strong>Формат JSON:</strong><br>
            {
                "syntax_tree": {...},
                "semantic_roles": [
                    {
                        "predicate": "глагол",
                        "agent": "субъект",
                        "counter_agent": "контрагент",
                        "patient": "объект",
                        "content": "содержание",
                        "addressee": "адресат",
                        "recipient": "получатель",
                        "instrument": "инструмент",
                        "means": "средство",
                        "location": "место",
                        "source": "начальная точка",
                        "destination": "конечная точка",
                        "route": "маршрут",
                        "manner": "способ",
                        "condition": "условие",
                        "motivation": "мотивировка",
                        "cause": "причина",
                        "result": "результат",
                        "purpose": "цель",
                        "aspect": "аспект",
                        "quantity": "количество",
                        "duration": "срок",
                        "time": "время",
                        "material": "материал",
                        "price": "цена"
                    }
                ],
                "semantic_relations": [...],
                "valency_frame": {...},
                "summary": {...}
            }
        </div>
    `;
    
    document.body.appendChild(overlay);
    document.body.appendChild(editor);
    
    const textarea = editor.querySelector('#semantic-editor-textarea');
    
    editor.querySelector('#save-semantic-btn').onclick = async () => {
        try {
            const updatedAnalysis = JSON.parse(textarea.value);
            
            const response = await fetch('/api/update_semantic_analysis', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    session_id: 'web_session',
                    message_index: messageIndex,
                    semantic_analysis: updatedAnalysis
                })
            });
            
            const data = await response.json();
            if (data.success) {
                message.semanticAnalysis = updatedAnalysis;
                currentSemanticAnalysis = updatedAnalysis;
                renderSemanticAnalysis(updatedAnalysis);
                alert('Семантический анализ обновлен');
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
    
    editor.querySelector('#cancel-semantic-btn').onclick = () => {
        editor.remove();
        overlay.remove();
    };
}