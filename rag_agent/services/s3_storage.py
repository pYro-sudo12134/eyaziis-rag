import boto3
from botocore.exceptions import ClientError
from typing import Optional, List, Dict, Any, BinaryIO
import io
import json
import logging
from datetime import datetime
from ..config import config

logger = logging.getLogger(__name__)


class S3StorageService:
    """
    Сервис для работы с S3-совместимым хранилищем (LocalStack, AWS S3)
    """
    
    def __init__(self):
        s3_config = config.get_s3_config()
        
        self.endpoint_url = s3_config['endpoint_url']
        self.bucket_name = s3_config['bucket_name']
        self.results_prefix = s3_config['results_prefix']
        self.uploads_prefix = s3_config['uploads_prefix']
        
        self.s3_client = boto3.client(
            's3',
            endpoint_url=self.endpoint_url,
            aws_access_key_id=s3_config['aws_access_key_id'],
            aws_secret_access_key=s3_config['aws_secret_access_key'],
            region_name=s3_config['region_name'],
            use_ssl=False,
            verify=False
        )
        
        self._ensure_bucket()
    
    def _ensure_bucket(self):
        """Создает bucket если он не существует"""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"Bucket {self.bucket_name} already exists")
        except ClientError:
            try:
                self.s3_client.create_bucket(Bucket=self.bucket_name)
                logger.info(f"Created bucket: {self.bucket_name}")
                
                self.s3_client.put_bucket_versioning(
                    Bucket=self.bucket_name,
                    VersioningConfiguration={'Status': 'Enabled'}
                )
                logger.info(f"Enabled versioning for bucket: {self.bucket_name}")
                
            except Exception as e:
                logger.error(f"Error creating bucket: {e}")
                raise
    
    def upload_file(self, 
                    file_obj: BinaryIO, 
                    key: str, 
                    metadata: Optional[Dict] = None,
                    content_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Загружает файл в S3
        
        Args:
            file_obj: файловый объект или байты
            key: путь/ключ в S3
            metadata: метаданные
            content_type: MIME тип
            
        Returns:
            Dict с информацией о загрузке
        """
        try:
            extra_args = {}
            if metadata:
                extra_args['Metadata'] = metadata
            if content_type:
                extra_args['ContentType'] = content_type
            
            if isinstance(file_obj, str):
                file_obj = io.BytesIO(file_obj.encode('utf-8'))
            elif isinstance(file_obj, dict):
                file_obj = io.BytesIO(json.dumps(file_obj).encode('utf-8'))
                if not content_type:
                    extra_args['ContentType'] = 'application/json'
            
            self.s3_client.upload_fileobj(
                file_obj,
                self.bucket_name,
                key,
                ExtraArgs=extra_args if extra_args else None
            )
            
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
            
            return {
                'success': True,
                'key': key,
                'bucket': self.bucket_name,
                'etag': response.get('ETag', '').strip('"'),
                'size': response.get('ContentLength', 0),
                'last_modified': response.get('LastModified').isoformat() if response.get('LastModified') else None,
                'url': f"{self.endpoint_url}/{self.bucket_name}/{key}"
            }
            
        except ClientError as e:
            logger.error(f"Error uploading to S3: {e}")
            return {
                'success': False,
                'error': str(e),
                'key': key
            }
    
    def download_file(self, key: str) -> Optional[bytes]:
        """Скачивает файл из S3"""
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
            return response['Body'].read()
        except ClientError as e:
            logger.error(f"Error downloading from S3: {e}")
            return None
    
    def download_file_to_stream(self, key: str) -> Optional[BinaryIO]:
        """Скачивает файл в поток"""
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
            return response['Body']
        except ClientError as e:
            logger.error(f"Error downloading from S3: {e}")
            return None
    
    def delete_file(self, key: str) -> bool:
        """Удаляет файл из S3"""
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError as e:
            logger.error(f"Error deleting from S3: {e}")
            return False
    
    def list_files(self, prefix: str = "", max_keys: int = 1000) -> List[Dict[str, Any]]:
        """Список файлов в S3"""
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                MaxKeys=max_keys
            )
            
            files = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    files.append({
                        'key': obj['Key'],
                        'size': obj['Size'],
                        'last_modified': obj['LastModified'].isoformat(),
                        'etag': obj['ETag'].strip('"')
                    })
            
            return files
            
        except ClientError as e:
            logger.error(f"Error listing files: {e}")
            return []
    
    def get_file_info(self, key: str) -> Optional[Dict[str, Any]]:
        """Получает информацию о файле"""
        try:
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
            return {
                'key': key,
                'size': response.get('ContentLength', 0),
                'last_modified': response.get('LastModified').isoformat() if response.get('LastModified') else None,
                'content_type': response.get('ContentType'),
                'metadata': response.get('Metadata', {})
            }
        except ClientError as e:
            logger.error(f"Error getting file info: {e}")
            return None
    
    def save_json(self, data: Dict[str, Any], key: str) -> Dict[str, Any]:
        """Сохраняет JSON в S3"""
        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        return self.upload_file(
            io.BytesIO(json_str.encode('utf-8')),
            key,
            content_type='application/json'
        )
    
    def load_json(self, key: str) -> Optional[Dict[str, Any]]:
        """Загружает JSON из S3"""
        content = self.download_file(key)
        if content:
            try:
                return json.loads(content.decode('utf-8'))
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing JSON: {e}")
                return None
        return None
    
    def save_result(self, result_data: Dict[str, Any], filename: str) -> Dict[str, Any]:
        """Сохраняет результат анализа в S3"""
        key = f"{self.results_prefix}{filename}"
        return self.save_json(result_data, key)
    
    def load_result(self, filename: str) -> Optional[Dict[str, Any]]:
        """Загружает результат анализа из S3"""
        key = f"{self.results_prefix}{filename}"
        return self.load_json(key)
    
    def list_results(self) -> List[Dict[str, Any]]:
        """Список сохраненных результатов"""
        files = self.list_files(prefix=self.results_prefix)
        
        results = []
        for file in files:
            filename = file['key'].replace(self.results_prefix, '')
            if filename and not filename.startswith('history/'):
                results.append({
                    'filename': filename,
                    'size': file['size'],
                    'modified': file['last_modified'],
                    'key': file['key']
                })
        
        return sorted(results, key=lambda x: x['modified'], reverse=True)
    
    def delete_result(self, filename: str) -> bool:
        """Удаляет результат из S3"""
        key = f"{self.results_prefix}{filename}"
        return self.delete_file(key)
    
    def save_upload(self, file_obj: BinaryIO, filename: str, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """Сохраняет загруженный файл в S3"""
        key = f"{self.uploads_prefix}{filename}"
        return self.upload_file(file_obj, key, metadata)
    
    def get_upload(self, filename: str) -> Optional[bytes]:
        """Получает загруженный файл из S3"""
        key = f"{self.uploads_prefix}{filename}"
        return self.download_file(key)
    
    def list_uploads(self) -> List[Dict[str, Any]]:
        """Список загруженных файлов"""
        files = self.list_files(prefix=self.uploads_prefix)
        
        uploads = []
        for file in files:
            filename = file['key'].replace(self.uploads_prefix, '')
            if filename:
                uploads.append({
                    'filename': filename,
                    'size': file['size'],
                    'modified': file['last_modified'],
                    'key': file['key']
                })
        
        return sorted(uploads, key=lambda x: x['modified'], reverse=True)
    
    def delete_upload(self, filename: str) -> bool:
        """Удаляет загруженный файл из S3"""
        key = f"{self.uploads_prefix}{filename}"
        return self.delete_file(key)
    
    def save_dialog_history(self, session_id: str, history: List[Dict]) -> Dict[str, Any]:
        """Сохраняет историю диалога"""
        key = f"{self.results_prefix}history/{session_id}.json"
        return self.save_json({
            'history': history,
            'session_id': session_id,
            'updated_at': datetime.now().isoformat()
        }, key)
    
    def load_dialog_history(self, session_id: str) -> Optional[List[Dict]]:
        """Загружает историю диалога"""
        key = f"{self.results_prefix}history/{session_id}.json"
        data = self.load_json(key)
        return data.get('history') if data else None
    
    def delete_dialog_history(self, session_id: str) -> bool:
        """Удаляет историю диалога"""
        key = f"{self.results_prefix}history/{session_id}.json"
        return self.delete_file(key)
    
    def list_dialog_histories(self) -> List[Dict[str, Any]]:
        """Список всех сохраненных историй диалогов"""
        files = self.list_files(prefix=f"{self.results_prefix}history/")
        
        histories = []
        for file in files:
            session_id = file['key'].replace(f"{self.results_prefix}history/", '').replace('.json', '')
            if session_id:
                histories.append({
                    'session_id': session_id,
                    'size': file['size'],
                    'modified': file['last_modified'],
                    'key': file['key']
                })
        
        return sorted(histories, key=lambda x: x['modified'], reverse=True)
    
    def get_stats(self) -> Dict[str, Any]:
        """Получает статистику S3 хранилища"""
        try:
            results = self.list_results()
            uploads = self.list_uploads()
            histories = self.list_dialog_histories()
            
            all_files = self.list_files()
            total_size = sum(f['size'] for f in all_files)
            
            return {
                'success': True,
                'bucket': self.bucket_name,
                'endpoint': self.endpoint_url,
                'total_files': len(all_files),
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'results_count': len(results),
                'uploads_count': len(uploads),
                'histories_count': len(histories)
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {
                'success': False,
                'error': str(e)
            }