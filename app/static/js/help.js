// Функция для загрузки полной справки в помощь
function loadFullHelp() {
    const helpContainer = document.getElementById('tab-help');
    if (!helpContainer) return;
    
    helpContainer.innerHTML = `
        <div class="help-section">
            <h4>О системе</h4>
            <p>RAG Agent - интеллектуальная система анализа текста c использованием Retrieval-Augmented Generation (RAG). Система сочетает семантический поиск по загруженным документам с генерацией ответов на основе LLM.</p>
        </div>
        
        <div class="help-section">
            <h4>Возможности</h4>
            <ul>
                <li><strong>Загрузка документов</strong> - поддерживаются TXT, PDF, DOCX, DOC, HTML, RTF форматы</li>
                <li><strong>Синтаксический анализ</strong> - построение дерева зависимостей предложения</li>
                <li><strong>Семантический анализ</strong> - выделение 25 типов семантических ролей (агент, контрагент, пациенс, инструмент, локация, адресат, получатель, средство, маршрут, способ, условие, причина, цель и др.)</li>
                <li><strong>Валентностная рамка</strong> - выделение обязательных и факультативных актантов</li>
                <li><strong>Сохранение результатов</strong> - экспорт анализа в S3 хранилище</li>
                <li><strong>Предметные области</strong> - Кинематограф, Животные</li>
                <li><strong>Редактирование сообщений, деревьев и семантики</strong></li>
            </ul>
        </div>
        
        <div class="help-section">
            <h4>Команды</h4>
            <div class="command-list">
                <div class="command-item"><span class="command-name">/help</span><span class="command-desc">Справка</span></div>
                <div class="command-item"><span class="command-name">/syntax [текст]</span><span class="command-desc">Синтаксическое дерево</span></div>
                <div class="command-item"><span class="command-name">/semantic [текст]</span><span class="command-desc">Семантический анализ</span></div>
                <div class="command-item"><span class="command-name">/save</span><span class="command-desc">Сохранить анализ</span></div>
                <div class="command-item"><span class="command-name">/stats</span><span class="command-desc">Статистика</span></div>
                <div class="command-item"><span class="command-name">/clear</span><span class="command-desc">Очистить историю</span></div>
            </div>
        </div>
        
        <div class="help-section">
            <h4>Горячие клавиши</h4>
            <div class="shortcut-grid">
                <div class="shortcut-item"><span class="shortcut-key">Enter</span> - отправить</div>
                <div class="shortcut-item"><span class="shortcut-key">Ctrl+Enter</span> - новая строка</div>
            </div>
        </div>
        
        <div class="help-section">
            <h4>FAQ</h4>
            <div class="faq-item">
                <div class="faq-question">Как редактировать сообщение?</div>
                <div class="faq-answer">Наведите курсор и нажмите "Редактировать"</div>
            </div>
            <div class="faq-item">
                <div class="faq-question">Как перегенерировать ответ?</div>
                <div class="faq-answer">Наведите курсор на ответ и нажмите "Перегенерировать"</div>
            </div>
            <div class="faq-item">
                <div class="faq-question">Какие форматы поддерживаются?</div>
                <div class="faq-answer">TXT, PDF, DOCX, DOC, HTML, RTF (до 50 МБ)</div>
            </div>
        </div>
    `;
}