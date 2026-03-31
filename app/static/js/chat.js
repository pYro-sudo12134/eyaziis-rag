// Основная логика чата
async function sendMessage() {
    const input = document.getElementById('messageInput');
    const message = input.value.trim();
    if (!message) return;
    
    if (message.startsWith('/')) {
        handleCommand(message);
        input.value = '';
        return;
    }
    
    currentText = message;
    addMessage('user', message);
    input.value = '';
    
    const loadingId = addLoadingMessage();
    
    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                message: message,
                include_syntax: true,
                session_id: 'web_session'
            })
        });
        
        const data = await response.json();
        removeLoadingMessage(loadingId);
        
        addMessage('assistant', data.response, null, data.syntax_tree, data.semantic_analysis);
        
        if (data.sources?.length) addSources(data.sources);
        if (data.syntax_tree) {
            currentSyntaxTree = data.syntax_tree;
            renderSyntaxTree(data.syntax_tree);
        }
        if (data.semantic_analysis) {
            currentSemanticAnalysis = data.semantic_analysis;
            renderSemanticAnalysis(data.semantic_analysis);
        }
        
        await saveHistory();
        
    } catch (error) {
        removeLoadingMessage(loadingId);
        addMessage('assistant', 'Извините, произошла ошибка. Попробуйте позже.');
    }
}

function handleCommand(command) {
    const cmd = command.toLowerCase().trim();
    
    const commands = {
        '/help': () => addMessage('assistant', 'Доступные команды:\n/help - справка\n/syntax [текст] - синтаксическое дерево\n/semantic [текст] - семантический анализ\n/save - сохранить анализ\n/stats - статистика\n/clear - очистить историю'),
        '/stats': () => loadStats(),
        '/clear': () => clearHistory(),
        '/save': () => {
            if (currentSyntaxTree) saveSyntaxTree();
            else if (currentSemanticAnalysis) saveSemanticAnalysis();
            else addMessage('assistant', 'Нет данных для сохранения');
        }
    };
    
    if (commands[cmd]) {
        commands[cmd]();
        return;
    }
    
    if (cmd.startsWith('/syntax ')) {
        const text = cmd.substring(7).trim();
        if (text) analyzeSyntaxOnly(text);
        else addMessage('assistant', 'Укажите текст для анализа. Пример: /syntax Кошка ловит мышь');
        return;
    }
    
    if (cmd.startsWith('/semantic ')) {
        const text = cmd.substring(9).trim();
        if (text) analyzeSemanticOnly(text);
        else addMessage('assistant', 'Укажите текст для анализа. Пример: /semantic Кошка ловит мышь');
        return;
    }
    
    addMessage('assistant', 'Неизвестная команда. Введите /help для списка команд.');
}