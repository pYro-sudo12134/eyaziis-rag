import os
import traceback
import json
import tempfile
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from rag_agent.agent import RAGAgent
from rag_agent.models.schemas import Query
from rag_agent.utils.document_parsers import DocumentParser, parse_document
from rag_agent.services.s3_storage import S3StorageService

app = Flask(__name__)
agent = RAGAgent()
parser = DocumentParser()
s3_storage = S3StorageService()

ALLOWED_EXTENSIONS = {'.txt', '.pdf', '.docx', '.doc', '.html', '.htm', '.rtf'}

app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

CORS(app, 
     origins=os.getenv('CORS_ORIGINS', '*').split(','),
     methods=os.getenv('CORS_METHODS', '*').split(','),
     allow_headers=['Content-Type', 'Authorization'])


@app.route('/')
def index():
    """Главная страница"""
    return render_template('index.html')


@app.route('/api/upload', methods=['POST', 'OPTIONS'])
def upload_document():
    """
    Загрузка документа для анализа в S3
    Поддерживает: TXT, PDF, DOCX, DOC, HTML, RTF
    """
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        filename = secure_filename(file.filename)
        ext = os.path.splitext(filename)[1].lower()
        
        if ext not in ALLOWED_EXTENSIONS:
            return jsonify({
                'error': f'File type not allowed. Supported: {", ".join(ALLOWED_EXTENSIONS)}'
            }), 400
        
        metadata = request.form.get('metadata')
        if metadata:
            try:
                metadata = json.loads(metadata)
            except:
                metadata = {}
        else:
            metadata = {}
        
        metadata['upload_time'] = datetime.now().isoformat()
        metadata['original_filename'] = file.filename
        metadata['content_type'] = file.content_type or 'application/octet-stream'
        
        upload_result = s3_storage.save_upload(file, filename, metadata)
        
        if not upload_result['success']:
            return jsonify({'error': upload_result['error']}), 500
        
        file_content = s3_storage.get_upload(filename)
        if not file_content:
            return jsonify({'error': 'Failed to read uploaded file from S3'}), 500
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp_file:
            tmp_file.write(file_content)
            tmp_path = tmp_file.name
        
        try:
            result = parse_document(tmp_path, metadata)
            
            if not result['success']:
                return jsonify({
                    'error': result['error'],
                    'file': filename
                }), 400
            
            index_result = agent.add_document(
                text=result['text'],
                metadata={
                    **result['metadata'],
                    'source_file': filename,
                    's3_key': upload_result['key'],
                    'upload_time': datetime.now().isoformat()
                }
            )
            
            return jsonify({
                'success': True,
                'message': 'Document uploaded and indexed successfully',
                'filename': filename,
                's3_key': upload_result['key'],
                'chunks': index_result['chunks_count'],
                'statistics': {
                    'char_count': result['metadata']['char_count'],
                    'word_count': result['metadata']['word_count'],
                    'line_count': result['metadata']['line_count']
                },
                'preview': result['text'][:500] + '...' if len(result['text']) > 500 else result['text']
            })
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    except Exception as e:
        print(f"Error uploading document: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/supported_formats', methods=['GET'])
def supported_formats():
    """Получить список поддерживаемых форматов"""
    return jsonify({
        'formats': list(ALLOWED_EXTENSIONS),
        'descriptions': {
            '.txt': 'Plain text files',
            '.pdf': 'PDF documents',
            '.docx': 'Microsoft Word documents (modern)',
            '.doc': 'Microsoft Word documents (legacy)',
            '.html': 'HTML web pages',
            '.htm': 'HTML web pages',
            '.rtf': 'Rich Text Format documents'
        }
    })


@app.route('/api/parse', methods=['POST', 'OPTIONS'])
def parse_document_endpoint():
    """
    Парсинг документа без индексации (только извлечение текста)
    Поддерживает файлы из S3 или локальные пути
    """
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        s3_key = data.get('s3_key')
        file_path = data.get('file_path')
        metadata = data.get('metadata', {})
        
        if s3_key:
            file_content = s3_storage.download_file(s3_key)
            if not file_content:
                return jsonify({'error': f'File not found in S3: {s3_key}'}), 404
            
            ext = os.path.splitext(s3_key)[1].lower()
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp_file:
                tmp_file.write(file_content)
                tmp_path = tmp_file.name
            
            try:
                result = parse_document(tmp_path, metadata)
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
        
        elif file_path:
            if not os.path.exists(file_path):
                return jsonify({'error': f'File not found: {file_path}'}), 404
            result = parse_document(file_path, metadata)
        
        else:
            return jsonify({'error': 'Either s3_key or file_path is required'}), 400
        
        if not result['success']:
            return jsonify({'error': result['error']}), 400
        
        return jsonify({
            'success': True,
            'text': result['text'],
            'metadata': result['metadata'],
            'statistics': {
                'char_count': result['metadata']['char_count'],
                'word_count': result['metadata']['word_count']
            }
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/save_result', methods=['POST', 'OPTIONS'])
def save_analysis_result():
    """
    Сохранить результат анализа в S3
    (синтаксическое дерево, грамматический разбор и т.д.)
    """
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        text = data.get('text', '')
        syntax_tree = data.get('syntax_tree', {})
        analysis = data.get('analysis', {})
        analysis_type = data.get('type', 'syntax')
        grammar_analysis = data.get('grammar_analysis', None)
        metadata = data.get('metadata', {})
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{analysis_type}_{timestamp}.json"
        
        result_data = {
            'type': analysis_type,
            'timestamp': timestamp,
            'datetime': datetime.now().isoformat(),
            'text': text,
            'syntax_tree': syntax_tree,
            'metadata': metadata
        }
        
        if grammar_analysis:
            result_data['grammar_analysis'] = grammar_analysis
        
        if analysis:
            result_data['analysis'] = analysis

        save_result = s3_storage.save_result(result_data, filename)
        
        if not save_result['success']:
            return jsonify({'error': save_result['error']}), 500
        
        return jsonify({
            'success': True,
            'filename': filename,
            's3_key': save_result['key'],
            'message': f'Result saved as {filename}'
        })
    
    except Exception as e:
        print(f"Error saving result: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/load_result/<filename>', methods=['GET'])
def load_analysis_result(filename):
    """Загрузить сохраненный результат из S3"""
    try:
        data = s3_storage.load_result(filename)
        
        if not data:
            return jsonify({'error': 'File not found'}), 404
        
        return jsonify(data)
    
    except Exception as e:
        print(f"Error loading result: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/list_results', methods=['GET'])
def list_analysis_results():
    """Список сохраненных результатов из S3"""
    try:
        results = s3_storage.list_results()
        
        return jsonify({
            'success': True,
            'results': results
        })
    
    except Exception as e:
        print(f"Error listing results: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/delete_result/<filename>', methods=['DELETE'])
def delete_analysis_result(filename):
    """Удалить сохраненный результат из S3"""
    try:
        success = s3_storage.delete_result(filename)
        
        if success:
            return jsonify({
                'success': True, 
                'message': f'Deleted {filename}'
            })
        else:
            return jsonify({'error': 'Failed to delete file'}), 500
    
    except Exception as e:
        print(f"Error deleting result: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/history/<session_id>', methods=['GET', 'POST', 'DELETE', 'OPTIONS'])
def dialog_history(session_id):
    """
    Управление историей диалога в S3
    GET - получить историю
    POST - сохранить историю
    DELETE - удалить историю
    """
    if request.method == 'OPTIONS':
        return '', 200
    
    if request.method == 'GET':
        try:
            history = s3_storage.load_dialog_history(session_id)
            return jsonify({
                'success': True,
                'session_id': session_id,
                'history': history or []
            })
        except Exception as e:
            print(f"Error loading history: {e}")
            return jsonify({'error': str(e)}), 500
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            history = data.get('history', [])
            
            result = s3_storage.save_dialog_history(session_id, history)
            
            if result['success']:
                return jsonify({
                    'success': True,
                    'session_id': session_id,
                    'message': 'History saved',
                    's3_key': result['key']
                })
            else:
                return jsonify({'error': result['error']}), 500
                
        except Exception as e:
            print(f"Error saving history: {e}")
            return jsonify({'error': str(e)}), 500
    
    elif request.method == 'DELETE':
        try:
            success = s3_storage.delete_dialog_history(session_id)
            
            if success:
                return jsonify({
                    'success': True,
                    'session_id': session_id,
                    'message': 'History deleted'
                })
            else:
                return jsonify({'error': 'Failed to delete history'}), 500
                
        except Exception as e:
            print(f"Error deleting history: {e}")
            return jsonify({'error': str(e)}), 500


@app.route('/api/domain', methods=['GET', 'POST', 'OPTIONS'])
def domain():
    """
    Управление предметной областью
    GET - получить текущую область и примеры вопросов
    POST - установить новую область
    """
    if request.method == 'OPTIONS':
        return '', 200
    
    domain_config = {
        'current_domain': os.getenv('CURRENT_DOMAIN', 'cinema'),
        'domains': {
            'cinema': {
                'name': 'Кинематограф',
                'description': 'Вопросы о фильмах, актерах, режиссерах, истории кино',
                'examples': [
                    'Какие фильмы снимал Тарантино?',
                    'Расскажи о фильме "Побег из Шоушенка"',
                    'Кто такой Стивен Спилберг?',
                    'Какие фильмы получили Оскар в 2020 году?',
                    'Назови лучшие фильмы Кристофера Нолана'
                ]
            },
            'animals': {
                'name': 'Животные',
                'description': 'Виды животных, их повадки, среда обитания',
                'examples': [
                    'Какие животные живут в Африке?',
                    'Расскажи о пандах',
                    'Чем отличается верблюд от ламы?',
                    'Какие животные впадают в спячку?',
                    'Чем питаются киты?'
                ]
            }
        }
    }
    
    if request.method == 'GET':
        domain_name = domain_config['current_domain']
        domain_info = domain_config['domains'].get(domain_name, {})
        
        return jsonify({
            'success': True,
            'current_domain': domain_name,
            'name': domain_info.get('name', ''),
            'description': domain_info.get('description', ''),
            'examples': domain_info.get('examples', [])
        })
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            new_domain = data.get('domain')
            
            if new_domain not in domain_config['domains']:
                return jsonify({'error': f'Unknown domain: {new_domain}'}), 400
            
            domain_config['current_domain'] = new_domain
            
            domain_info = domain_config['domains'][new_domain]
            
            return jsonify({
                'success': True,
                'current_domain': new_domain,
                'name': domain_info['name'],
                'description': domain_info['description'],
                'examples': domain_info['examples']
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500


@app.route('/api/chat', methods=['POST', 'OPTIONS'])
def chat():
    """API чата с сохранением истории в S3"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        message = data.get('message', '')
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        
        include_syntax = data.get('include_syntax', True)
        session_id = data.get('session_id', 'default_session')
        
        query = Query(text=message, session_id=session_id)
        answer = agent.answer(query, include_syntax=include_syntax)
        
        history = s3_storage.load_dialog_history(session_id) or []
        history.append({
            'role': 'user',
            'content': message,
            'timestamp': datetime.now().isoformat()
        })
        history.append({
            'role': 'assistant',
            'content': answer.text,
            'timestamp': datetime.now().isoformat(),
            'syntax_tree': answer.syntax_tree
        })
        
        s3_storage.save_dialog_history(session_id, history)
        
        return jsonify({
            'response': answer.text,
            'syntax_tree': answer.syntax_tree,
            'sources': [{'text': s.text, 'score': s.score} for s in answer.sources]
        })
    
    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/syntax', methods=['POST', 'OPTIONS'])
def syntax():
    """API синтаксического разбора"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        text = data.get('text', '')
        if not text:
            return jsonify({'error': 'Text is required'}), 400
        
        tree = agent.get_syntax(text)
        return jsonify(tree)
    
    except Exception as e:
        print(f"Error in syntax endpoint: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/add_document', methods=['POST', 'OPTIONS'])
def add_document():
    """Добавление документа (текстовая версия)"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        text = data.get('text', '')
        if not text:
            return jsonify({'error': 'Text is required'}), 400
        
        metadata = data.get('metadata', {})
        
        result = agent.add_document(text, metadata)
        return jsonify(result)
    
    except Exception as e:
        print(f"Error in add_document endpoint: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/search', methods=['POST', 'OPTIONS'])
def search():
    """Поиск без генерации"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        query = data.get('query', '')
        if not query:
            return jsonify({'error': 'Query is required'}), 400
        
        top_k = data.get('top_k')
        
        results = agent.search(query, top_k)
        return jsonify(results)
    
    except Exception as e:
        print(f"Error in search endpoint: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/analyze_text', methods=['POST', 'OPTIONS'])
def analyze_text():
    """
    Анализ произвольного текста через LLM
    Отправляет текст на синтаксический разбор и возвращает дерево зависимостей
    """
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        text = data.get('text', '')
        if not text:
            return jsonify({'error': 'Text is required'}), 400
        
        syntax_tree = agent.get_syntax(text)
        
        include_grammar = data.get('include_grammar', False)
        
        result = {
            'success': True,
            'text': text,
            'syntax_tree': syntax_tree,
            'analysis': {
                'type': 'syntactic',
                'method': 'llm',
                'model': agent.llm.model
            }
        }
        
        if include_grammar:
            grammar_prompt = f"""
            Выполни грамматический разбор предложения: "{text}"
            
            Верни JSON с:
            - part_of_speech: части речи для каждого слова
            - case: падеж
            - gender: род
            - number: число
            - tense: время (для глаголов)
            """
            
            grammar_analysis = agent.llm.generate_json(grammar_prompt)
            result['grammar_analysis'] = grammar_analysis
        
        return jsonify(result)
    
    except Exception as e:
        print(f"Error in analyze_text endpoint: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/compare_syntax', methods=['POST', 'OPTIONS'])
def compare_syntax():
    """
    Сравнение синтаксического анализа двух текстов
    """
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        text1 = data.get('text1', '')
        text2 = data.get('text2', '')
        
        if not text1 or not text2:
            return jsonify({'error': 'Both text1 and text2 are required'}), 400
        
        tree1 = agent.get_syntax(text1)
        tree2 = agent.get_syntax(text2)
        
        comparison_prompt = f"""
        Сравни синтаксическую структуру двух предложений:
        
        Предложение 1: "{text1}"
        Структура: {tree1}
        
        Предложение 2: "{text2}"
        Структура: {tree2}
        
        Ответь в формате JSON:
        {{
            "similarities": ["сходство 1", "сходство 2"],
            "differences": ["различие 1", "различие 2"],
            "complexity_comparison": "какое предложение сложнее и почему",
            "structures": {{
                "type1": "тип структуры первого предложения",
                "type2": "тип структуры второго предложения"
            }}
        }}
        """
        
        comparison = agent.llm.generate_json(comparison_prompt, temperature=0.3)
        
        return jsonify({
            'success': True,
            'text1': text1,
            'text2': text2,
            'syntax_tree1': tree1,
            'syntax_tree2': tree2,
            'comparison': comparison
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/batch_analyze', methods=['POST', 'OPTIONS'])
def batch_analyze():
    """
    Пакетный анализ нескольких текстов
    """
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        if not data or 'texts' not in data:
            return jsonify({'error': 'Texts array is required'}), 400
        
        texts = data.get('texts', [])
        if not texts:
            return jsonify({'error': 'Empty texts array'}), 400
        
        results = []
        for i, text in enumerate(texts):
            try:
                syntax_tree = agent.get_syntax(text)
                results.append({
                    'index': i,
                    'text': text,
                    'syntax_tree': syntax_tree,
                    'success': True
                })
            except Exception as e:
                results.append({
                    'index': i,
                    'text': text,
                    'error': str(e),
                    'success': False
                })
        
        return jsonify({
            'success': True,
            'total': len(texts),
            'successful': len([r for r in results if r['success']]),
            'results': results
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/stats', methods=['GET'])
def stats():
    """Статистика агента и S3 хранилища"""
    try:
        stats = agent.get_stats()
        
        try:
            results_list = s3_storage.list_results()
            stats['s3_storage'] = {
                'results_count': len(results_list),
                'bucket': s3_storage.bucket_name,
                'endpoint': s3_storage.endpoint_url
            }
        except Exception as e:
            stats['s3_storage'] = {'error': str(e)}
        
        return jsonify(stats)
    
    except Exception as e:
        print(f"Error in stats endpoint: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/s3_browse', methods=['GET'])
def s3_browse():
    """
    Просмотр содержимого S3 bucket
    """
    try:
        prefix = request.args.get('prefix', '')
        
        files = s3_storage.list_files(prefix=prefix)
        
        return jsonify({
            'success': True,
            'bucket': s3_storage.bucket_name,
            'prefix': prefix,
            'files': files
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/semantic_analysis', methods=['POST', 'OPTIONS'])
def semantic_analysis_endpoint():
    """
    Полный семантико-синтаксический анализ текста.
    Возвращает синтаксическое дерево + семантические роли + отношения.
    """
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        text = data.get('text', '')
        if not text:
            return jsonify({'error': 'Text is required'}), 400
        
        include_syntax = data.get('include_syntax', True)
        
        analysis = agent.semantic_analysis(text)
        
        if not include_syntax and 'syntax_tree' in analysis:
            del analysis['syntax_tree']
        
        save = data.get('save', False)
        if save:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"semantic_analysis_{timestamp}.json"
            
            s3_storage.save_result({
                'type': 'semantic_analysis',
                'text': text,
                'analysis': analysis,
                'timestamp': timestamp,
                'datetime': datetime.now().isoformat()
            }, filename)
            analysis['saved_as'] = filename
        
        return jsonify({
            'success': True,
            'text': text,
            'analysis': analysis
        })
    
    except Exception as e:
        print(f"Error in semantic_analysis endpoint: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/semantic_roles', methods=['POST', 'OPTIONS'])
def semantic_roles_endpoint():
    """
    Возвращает только семантические роли.
    """
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        text = data.get('text', '')
        if not text:
            return jsonify({'error': 'Text is required'}), 400
        
        roles = agent.get_semantic_roles(text)
        
        return jsonify({
            'success': True,
            'text': text,
            'semantic_roles': roles
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/semantic_relations', methods=['POST', 'OPTIONS'])
def semantic_relations_endpoint():
    """
    Возвращает семантические отношения между словами.
    """
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        text = data.get('text', '')
        if not text:
            return jsonify({'error': 'Text is required'}), 400
        
        relations = agent.get_semantic_relations(text)
        
        return jsonify({
            'success': True,
            'text': text,
            'semantic_relations': relations
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/update_syntax_tree', methods=['POST', 'OPTIONS'])
def update_syntax_tree():
    """
    Обновить синтаксическое дерево (после ручного редактирования)
    """
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        session_id = data.get('session_id', 'default_session')
        message_index = data.get('message_index')
        updated_tree = data.get('syntax_tree')
        
        if message_index is None or not updated_tree:
            return jsonify({'error': 'message_index and syntax_tree are required'}), 400
        
        history = s3_storage.load_dialog_history(session_id) or []
        
        for i, msg in enumerate(history):
            if i == message_index and msg.get('role') == 'assistant':
                msg['syntax_tree'] = updated_tree
                msg['edited'] = True
                msg['edited_at'] = datetime.now().isoformat()
                break
        
        s3_storage.save_dialog_history(session_id, history)
        
        return jsonify({
            'success': True,
            'message': 'Syntax tree updated',
            'session_id': session_id,
            'message_index': message_index
        })
        
    except Exception as e:
        print(f"Error updating syntax tree: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/update_message', methods=['POST', 'OPTIONS'])
def update_message():
    """
    Обновить сообщение в истории чата
    """
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        session_id = data.get('session_id', 'default_session')
        message_index = data.get('message_index')
        new_content = data.get('content')
        role = data.get('role')
        
        if message_index is None or not new_content:
            return jsonify({'error': 'message_index and content are required'}), 400
        
        history = s3_storage.load_dialog_history(session_id) or []
        
        if 0 <= message_index < len(history):
            history[message_index]['content'] = new_content
            if role:
                history[message_index]['role'] = role
            history[message_index]['edited'] = True
            history[message_index]['edited_at'] = datetime.now().isoformat()
        else:
            return jsonify({'error': 'Message index out of range'}), 400
        
        s3_storage.save_dialog_history(session_id, history)
        
        return jsonify({
            'success': True,
            'message': 'Message updated',
            'session_id': session_id,
            'message_index': message_index
        })
        
    except Exception as e:
        print(f"Error updating message: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/delete_message', methods=['POST', 'OPTIONS'])
def delete_message():
    """
    Удалить сообщение из истории чата
    """
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        session_id = data.get('session_id', 'default_session')
        message_index = data.get('message_index')
        
        if message_index is None:
            return jsonify({'error': 'message_index is required'}), 400
        
        history = s3_storage.load_dialog_history(session_id) or []
        
        if 0 <= message_index < len(history):
            deleted = history.pop(message_index)
        else:
            return jsonify({'error': 'Message index out of range'}), 400
        
        s3_storage.save_dialog_history(session_id, history)
        
        return jsonify({
            'success': True,
            'message': 'Message deleted',
            'session_id': session_id,
            'deleted_message': deleted
        })
        
    except Exception as e:
        print(f"Error deleting message: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/regenerate_response', methods=['POST', 'OPTIONS'])
def regenerate_response():
    """
    Перегенерировать ответ ассистента
    """
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        session_id = data.get('session_id', 'default_session')
        message_index = data.get('message_index')
        
        if message_index is None:
            return jsonify({'error': 'message_index is required'}), 400
        
        history = s3_storage.load_dialog_history(session_id) or []
        
        user_message = None
        for i in range(message_index - 1, -1, -1):
            if history[i].get('role') == 'user':
                user_message = history[i].get('content')
                break
        
        if not user_message:
            return jsonify({'error': 'No user message found before this response'}), 400
        
        query = Query(text=user_message, session_id=session_id)
        new_answer = agent.answer(query, include_syntax=True)
        
        if 0 <= message_index < len(history) and history[message_index].get('role') == 'assistant':
            history[message_index]['content'] = new_answer.text
            history[message_index]['syntax_tree'] = new_answer.syntax_tree
            history[message_index]['regenerated'] = True
            history[message_index]['regenerated_at'] = datetime.now().isoformat()
            history[message_index]['original_content'] = history[message_index].get('content')
        
        s3_storage.save_dialog_history(session_id, history)
        
        return jsonify({
            'success': True,
            'message': 'Response regenerated',
            'new_content': new_answer.text,
            'syntax_tree': new_answer.syntax_tree,
            'message_index': message_index
        })
        
    except Exception as e:
        print(f"Error regenerating response: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    """Обработка 404 ошибок"""
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    """Обработка 500 ошибок"""
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)