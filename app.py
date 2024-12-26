from flask import Flask, request, send_file, render_template, current_app, after_this_request, jsonify, session
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from PIL import Image
import io
import os
import zipfile
from werkzeug.utils import secure_filename
import tempfile
import shutil
import logging
from moviepy.editor import VideoFileClip
from pydub import AudioSegment
import magic
import traceback
import requests
from bs4 import BeautifulSoup
import time
import subprocess
from urllib.parse import urljoin, urlparse
from flask_mail import Mail, Message
import re
import base64
import uuid

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'  # مطلوب لاستخدام session
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # Increase to 500MB max-limit
app.config['MAX_VIDEO_SIZE'] = 500 * 1024 * 1024  # 500MB for videos
app.config['ALLOWED_VIDEO_EXTENSIONS'] = {'mp4', 'avi', 'mov', 'mkv', 'wmv', 'flv', 'webm'}

def allowed_file(filename, allowed_extensions):
    """التحقق من امتداد الملف"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# إعدادات البريد الإلكتروني
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'hamzaxnine@gmail.com'
app.config['MAIL_PASSWORD'] = 'orcc jjlu xpsx joyn'
app.config['MAIL_DEFAULT_SENDER'] = 'hamzaxnine@gmail.com'
app.config['MAIL_MAX_EMAILS'] = None
app.config['MAIL_ASCII_ATTACHMENTS'] = False

# تهيئة Flask-Mail بعد تكوين جميع الإعدادات
mail = Mail(app)

# إضافة تسجيل الأخطاء
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# إضافة متغير عام لتخزين مسارات الملفات المضغوطة
zip_files = {}

def compress_image(image_file, quality, max_width=1920):
    try:
        img = Image.open(image_file)
        current_app.logger.info(f"Processing image: {image_file.filename}, Original size: {img.size}")
        
        if img.width > max_width:
            ratio = max_width / img.width
            new_height = int(img.height * ratio)
            img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
            current_app.logger.info(f"Resized image to: {img.size}")
        
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
            current_app.logger.info(f"Converted image mode from {img.mode} to RGB")
        
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=quality, optimize=True)
        output.seek(0)
        
        current_app.logger.info(f"Compressed image size: {len(output.getvalue())} bytes")
        return output
    except Exception as e:
        current_app.logger.error(f"Error compressing image: {str(e)}\n{traceback.format_exc()}")
        raise

def download_media_from_website(url, download_images=True, sid=None, download_id=None):
    try:
        # Validate URL
        if not url.startswith(('http://', 'https://')):
            raise ValueError('يرجى إدخال رابط صحيح يبدأ بـ http:// أو https://')

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        temp_dir = tempfile.mkdtemp()
        images_folder = os.path.join(temp_dir, "images")
        
        if download_images:
            os.makedirs(images_folder, exist_ok=True)
        
        result = {
            "success": False,
            "message": "",
            "zip_name": f"download_{timestamp}.zip",
            "total_files": 0,
            "downloaded_files": 0
        }

        # إنشاء ملف ZIP مباشرة
        zip_path = os.path.join(temp_dir, f"{download_id}.zip")
        zip_files[download_id] = zip_path  # تخزين مسار الملف المضغوط
        app.logger.info(f"Creating zip file at: {zip_path}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
        except requests.RequestException as e:
            raise ValueError(f'خطأ في الاتصال بالموقع: {str(e)}')
        
        if download_images:
            images = set()
            
            # البحث عن الصور بطرق مختلفة
            for img in soup.find_all('img'):
                for attr in ['src', 'data-src', 'data-original', 'data-lazy-src', 'data-original-src']:
                    src = img.get(attr)
                    if src:
                        images.add(src)
            
            for elem in soup.find_all(['div', 'section', 'a']):
                style = elem.get('style', '')
                if 'background-image' in style:
                    matches = re.findall(r'url\([\'"]?(.*?)[\'"]?\)', style)
                    images.update(matches)
            
            for meta in soup.find_all('meta'):
                content = meta.get('content', '')
                if content and (content.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp'))):
                    images.add(content)
            
            for link in soup.find_all('a', href=True):
                href = link['href']
                if href.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
                    images.add(href)
            
            for source in soup.find_all('source'):
                srcset = source.get('srcset', '')
                if srcset:
                    urls = re.findall(r'(https?://[^\s\'"]+)', srcset)
                    images.update(urls)
            
            images = {urljoin(url, img_url) if not img_url.startswith(('http://', 'https://')) else img_url 
                     for img_url in images}
            
            images = {img_url for img_url in images 
                     if img_url.startswith(('http://', 'https://')) and 
                     any(img_url.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg'])}
            
            total_images = len(images)
            result["total_files"] = total_images
            
            if total_images == 0:
                raise ValueError('لم يتم العثور على صور في هذا الموقع')
            
            if sid:
                socketio.emit('download_progress', {
                    'progress': 0,
                    'message': f'تم العثور على {total_images} صورة',
                }, room=sid)
            
            for index, img_url in enumerate(images, 1):
                try:
                    filename = os.path.basename(urlparse(img_url).path)
                    if not filename or '.' not in filename:
                        ext = '.jpg'
                        if 'image/png' in requests.head(img_url, headers=headers).headers.get('content-type', ''):
                            ext = '.png'
                        elif 'image/gif' in requests.head(img_url, headers=headers).headers.get('content-type', ''):
                            ext = '.gif'
                        elif 'image/webp' in requests.head(img_url, headers=headers).headers.get('content-type', ''):
                            ext = '.webp'
                        filename = f"image_{index}{ext}"
                    
                    filename = secure_filename(filename)
                    if not filename:
                        filename = f"image_{index}.jpg"
                    
                    img_response = requests.get(img_url, headers=headers, timeout=10)
                    img_response.raise_for_status()
                    
                    content_type = img_response.headers.get('content-type', '')
                    if not content_type.startswith('image/'):
                        continue

                    # حفظ الصورة في الذاكرة
                    img_data = img_response.content
                    
                    # إضافة الصورة إلى ملف ZIP مباشرة
                    with zipfile.ZipFile(zip_path, 'a') as zip_file:
                        zip_file.writestr(f"images/{filename}", img_data)
                    
                    result["downloaded_files"] += 1
                    
                    # إرسال الصورة عبر WebSocket
                    if sid:
                        img_base64 = base64.b64encode(img_data).decode('utf-8')
                        socketio.emit('image_downloaded', {
                            'image': img_base64,
                            'filename': filename
                        }, room=sid)
                    
                    progress = int((result["downloaded_files"] / total_images) * 100)
                    if sid:
                        socketio.emit('download_progress', {
                            'progress': progress,
                            'message': f'جاري تحميل الصور... ({result["downloaded_files"]}/{total_images})'
                        }, room=sid)
                            
                except Exception as e:
                    current_app.logger.error(f"Error downloading image {img_url}: {str(e)}")
                    continue
        
        if result["downloaded_files"] == 0:
            raise ValueError("لم يتم تحميل أي صور بنجاح")
        
        result["success"] = True
        result["message"] = f"تم تحميل {result['downloaded_files']} من {result['total_files']} صورة"
        
        return result
        
    except Exception as e:
        error_message = str(e)
        if sid:
            socketio.emit('download_error', {
                'error': error_message
            }, room=sid)
        raise ValueError(error_message)
    
    finally:
        try:
            if 'zip_file' in locals():
                zip_file.close()
        except:
            pass

@socketio.on('start_download')
def handle_download_request(data):
    url = data.get('url')
    if not url:
        emit('download_error', {'error': 'الرجاء إدخال رابط الموقع'})
        return
    
    try:
        # إنشاء معرف فريد للتحميل
        download_id = str(uuid.uuid4())
        
        result = download_media_from_website(url, download_images=True, sid=request.sid, download_id=download_id)
        if result['success']:
            emit('download_complete', {
                'success': True,
                'message': result['message'],
                'download_id': download_id
            })
    except Exception as e:
        emit('download_error', {'error': str(e)})

@app.route('/get-zip/<download_id>')
def get_zip(download_id):
    try:
        app.logger.info(f"Attempting to get zip file for ID: {download_id}")
        app.logger.info(f"Available zip files: {list(zip_files.keys())}")
        
        zip_path = zip_files.get(download_id)
        if zip_path and os.path.exists(zip_path):
            app.logger.info(f"Found zip file at: {zip_path}")
            
            @after_this_request
            def remove_file(response):
                try:
                    os.remove(zip_path)
                    zip_files.pop(download_id, None)
                    app.logger.info(f"Cleaned up zip file: {zip_path}")
                except Exception as e:
                    app.logger.error(f"Error removing zip file: {e}")
                return response
                
            return send_file(
                zip_path,
                mimetype='application/zip',
                as_attachment=True,
                download_name='images.zip'
            )
        else:
            app.logger.error(f"Zip file not found for ID: {download_id}")
            app.logger.error(f"Zip path: {zip_path}")
            return jsonify({'error': 'الملف غير موجود'}), 404
    except Exception as e:
        app.logger.error(f"Error in get_zip: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/compress-images', methods=['POST'])
def compress_images():
    try:
        if 'images[]' not in request.files:
            return jsonify({'error': 'لم يتم تحديد أي صور'}), 400

        files = request.files.getlist('images[]')
        if not files:
            return jsonify({'error': 'لم يتم العثور على صور'}), 400

        quality = int(request.form.get('quality', 80))

        # إنشاء مجلد مؤقت لحفظ الصور المضغوطة
        temp_dir = tempfile.mkdtemp()

        compressed_files = []
        for file in files:
            if file and allowed_file(file.filename, {'png', 'jpg', 'jpeg', 'gif', 'webp'}):
                try:
                    # حفظ الصورة الأصلية في المجلد المؤقت
                    original_path = os.path.join(temp_dir, secure_filename(file.filename))
                    file.save(original_path)

                    # ضغط الصورة
                    img = Image.open(original_path)
                    
                    # تحويل الصورة إلى RGB إذا كانت RGBA
                    if img.mode in ('RGBA', 'P'):
                        img = img.convert('RGB')
                    
                    # اسم الملف المضغوط
                    filename = os.path.splitext(secure_filename(file.filename))[0]
                    compressed_path = os.path.join(temp_dir, f"{filename}_compressed.jpg")
                    
                    # حفظ الصورة المضغوطة
                    img.save(compressed_path, 'JPEG', quality=quality, optimize=True)
                    compressed_files.append(compressed_path)
                except Exception as e:
                    app.logger.error(f"Error processing {file.filename}: {str(e)}")
                    continue

        if not compressed_files:
            return jsonify({'error': 'لم يتم ضغط أي صور بنجاح'}), 400

        # إنشاء ملف ZIP يحتوي على الصور المضغوطة
        zip_path = os.path.join(temp_dir, 'compressed_images.zip')
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for file in compressed_files:
                zipf.write(file, os.path.basename(file))

        @after_this_request
        def cleanup(response):
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                app.logger.error(f"Error cleaning up: {e}")
            return response

        # إرسال الملف المضغوط
        return send_file(
            zip_path,
            mimetype='application/zip',
            as_attachment=True,
            download_name='compressed_images.zip'
        )

    except Exception as e:
        app.logger.error(f"Error in compress_images: {str(e)}")
        return jsonify({'error': str(e)}), 400

@app.route('/api/video-converter', methods=['POST'])
def convert_video():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        # التحقق من حجم الملف
        if request.content_length > app.config['MAX_VIDEO_SIZE']:
            return jsonify({'error': 'File size exceeds the limit (500MB)'}), 413

        # التحقق من امتداد الملف
        if not allowed_file(file.filename, app.config['ALLOWED_VIDEO_EXTENSIONS']):
            return jsonify({'error': 'Invalid file type'}), 400

        # إنشاء اسم ملف آمن
        filename = secure_filename(file.filename)
        temp_folder = tempfile.mkdtemp()
        video_path = os.path.join(temp_folder, filename)
        
        # حفظ الملف
        file.save(video_path)
        
        try:
            # تحويل الفيديو إلى صوت
            output_format = request.form.get('format', 'mp3')
            video_clip = VideoFileClip(video_path)
            audio = video_clip.audio
            
            # إنشاء اسم الملف الناتج
            output_filename = f"{os.path.splitext(filename)[0]}.{output_format}"
            output_path = os.path.join(temp_folder, output_filename)
            
            # حفظ الملف الصوتي
            audio.write_audiofile(output_path)
            
            # إغلاق الملفات
            audio.close()
            video_clip.close()
            
            # إرسال الملف
            @after_this_request
            def cleanup(response):
                try:
                    shutil.rmtree(temp_folder)
                except Exception as e:
                    app.logger.error(f"Error cleaning up: {e}")
                return response
            
            return send_file(
                output_path,
                as_attachment=True,
                download_name=output_filename,
                mimetype=f'audio/{output_format}'
            )
            
        except Exception as e:
            # تنظيف الملفات في حالة حدوث خطأ
            try:
                shutil.rmtree(temp_folder)
            except:
                pass
            app.logger.error(f"Error converting video: {str(e)}\n{traceback.format_exc()}")
            return jsonify({'error': str(e)}), 500
            
    except Exception as e:
        app.logger.error(f"Error in convert_video: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'error': 'An unexpected error occurred'}), 500

@app.route('/api/convert-audio', methods=['POST'])
def convert_audio():
    try:
        if 'audio' not in request.files:
            return jsonify({'error': 'لم يتم تحديد ملف صوتي'}), 400
        
        audio_file = request.files['audio']
        target_format = request.form.get('format', 'mp3')  # الصيغة الافتراضية هي MP3
        
        if audio_file.filename == '':
            return jsonify({'error': 'لم يتم تحديد ملف صوتي'}), 400
        
        # التحقق من صيغة الملف
        supported_input_formats = {'.mp3', '.wav', '.aac', '.ogg', '.m4a', '.wma', '.flac', '.aif', '.aiff', 
                                 '.au', '.caf', '.dts', '.gsm', '.m4b', '.m4r', '.mka', '.mmf', '.mp2', 
                                 '.mpa', '.oga', '.opus', '.ra', '.voc'}
        if not any(audio_file.filename.lower().endswith(ext) for ext in supported_input_formats):
            return jsonify({'error': 'صيغة الملف الصوتي غير مدعومة'}), 400
        
        # التحقق من صيغة الصوت المطلوبة
        valid_formats = {'aac', 'aif', 'aiff', 'au', 'caf', 'dts', 'flac', 'gsm', 'm4a', 'm4b', 
                        'm4r', 'mka', 'mmf', 'mp2', 'mp3', 'mpa', 'oga', 'ogg', 'opus', 'ra', 
                        'voc', 'wav', 'wma'}
        if target_format not in valid_formats:
            return jsonify({'error': 'صيغة الصوت المطلوبة غير مدعومة'}), 400
        
        # إنشاء مجلد مؤقت للتحويل
        temp_dir = tempfile.mkdtemp()
        audio_path = os.path.join(temp_dir, secure_filename(audio_file.filename))
        output_path = os.path.join(temp_dir, f'output.{target_format}')
        
        try:
            # حفظ ملف الصوت
            audio_file.save(audio_path)
            
            # تحديد إعدادات الترميز حسب الصيغة
            codec_settings = {
                'mp3': ['-acodec', 'libmp3lame', '-ab', '192k'],
                'wav': ['-acodec', 'pcm_s16le'],
                'aac': ['-acodec', 'aac', '-ab', '192k'],
                'ogg': ['-acodec', 'libvorbis', '-ab', '192k'],
                'm4a': ['-acodec', 'aac', '-ab', '192k'],
                'flac': ['-acodec', 'flac'],
                'aif': ['-acodec', 'pcm_s16le'],
                'aiff': ['-acodec', 'pcm_s16le'],
                'au': ['-acodec', 'pcm_s16le'],
                'caf': ['-acodec', 'alac'],
                'dts': ['-acodec', 'dca'],
                'gsm': ['-acodec', 'libgsm'],
                'm4b': ['-acodec', 'aac', '-ab', '192k'],
                'm4r': ['-acodec', 'aac', '-ab', '192k'],
                'mka': ['-acodec', 'copy'],
                'mmf': ['-acodec', 'libgsm'],
                'mp2': ['-acodec', 'mp2', '-ab', '192k'],
                'mpa': ['-acodec', 'mp2', '-ab', '192k'],
                'oga': ['-acodec', 'libvorbis', '-ab', '192k'],
                'opus': ['-acodec', 'libopus', '-ab', '192k'],
                'ra': ['-acodec', 'real_144'],
                'voc': ['-acodec', 'pcm_s16le'],
                'wma': ['-acodec', 'wmav2', '-ab', '192k']
            }
            
            # تحويل الصوت
            command = [
                'ffmpeg',
                '-i', audio_path
            ]
            command.extend(codec_settings.get(target_format, ['-acodec', 'copy']))
            command.extend([
                '-ar', '44100',  # معدل العينة
                '-y',  # الكتابة فوق الملف إذا كان موجوداً
                output_path
            ])
            
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                raise Exception(f"فشل في تحويل الصوت: {stderr.decode()}")
            
            # تحديد نوع MIME للملف
            mime_types = {
                'mp3': 'audio/mpeg',
                'wav': 'audio/wav',
                'aac': 'audio/aac',
                'ogg': 'audio/ogg',
                'm4a': 'audio/mp4',
                'flac': 'audio/flac',
                'aif': 'audio/x-aiff',
                'aiff': 'audio/x-aiff',
                'au': 'audio/basic',
                'caf': 'audio/x-caf',
                'dts': 'audio/vnd.dts',
                'gsm': 'audio/x-gsm',
                'm4b': 'audio/mp4',
                'm4r': 'audio/mp4',
                'mka': 'audio/x-matroska',
                'mmf': 'application/vnd.smaf',
                'mp2': 'audio/mpeg',
                'mpa': 'audio/mpeg',
                'oga': 'audio/ogg',
                'opus': 'audio/opus',
                'ra': 'audio/vnd.rn-realaudio',
                'voc': 'audio/x-voc',
                'wma': 'audio/x-ms-wma'
            }
            
            # إرسال ملف الصوت
            return send_file(
                output_path,
                mimetype=mime_types.get(target_format, 'application/octet-stream'),
                as_attachment=True,
                download_name=f"{os.path.splitext(audio_file.filename)[0]}.{target_format}"
            )
            
        finally:
            # تنظيف الملفات المؤقتة
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                app.logger.error(f"Error cleaning up temp files: {e}")
                
    except Exception as e:
        app.logger.error(f"Error in convert_audio: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/download-images', methods=['POST'])
def download_images():
    try:
        data = request.get_json()
        url = data.get('url')
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400

        # استخدام BeautifulSoup لتحليل الصفحة
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # البحث عن جميع الصور في الصفحة
        images = []
        for img in soup.find_all('img'):
            img_url = img.get('src')
            if img_url:
                # التأكد من أن الرابط كامل
                if not img_url.startswith(('http://', 'https://')):
                    img_url = urljoin(url, img_url)
                images.append(img_url)
        
        return jsonify({'images': images})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download-images', methods=['POST'])
def download_images_route():
    url = request.json.get('url')
    if not url:
        return jsonify({'error': 'الرجاء إدخال رابط الموقع'}), 400
    
    try:
        # Get the Socket.IO session ID from the request if available
        sid = request.environ.get('socketio').sid if 'socketio' in request.environ else None
        
        # Create a unique download ID
        download_id = str(uuid.uuid4())
        
        # Download images with progress updates
        result = download_media_from_website(url, download_images=True, sid=sid, download_id=download_id)
        
        if result['success']:
            # Get the path to the zip file from the global dictionary
            zip_path = zip_files.get(download_id)
            
            if zip_path and os.path.exists(zip_path):
                app.logger.info(f"Zip file found at: {zip_path}")
                
                @after_this_request
                def cleanup(response):
                    try:
                        os.remove(zip_path)
                        zip_files.pop(download_id, None)
                        app.logger.info(f"Cleaned up zip file: {zip_path}")
                    except Exception as e:
                        app.logger.error(f"Error cleaning up: {e}")
                    return response
                
                return send_file(
                    zip_path,
                    mimetype='application/zip',
                    as_attachment=True,
                    download_name=result['zip_name']
                )
            else:
                app.logger.error(f"Zip file not found at: {zip_path}")
                return jsonify({'error': 'فشل في إنشاء ملف الضغط'}), 500
        else:
            return jsonify({'error': result['message']}), 400
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        app.logger.error(f"Error in download_images_route: {str(e)}")
        return jsonify({'error': 'حدث خطأ أثناء تحميل الصور'}), 500

@app.route('/send_message', methods=['POST'])
def send_message():
    try:
        data = request.json
        if not data:
            logger.error("No JSON data received")
            return jsonify({'status': 'error', 'message': 'لم يتم استلام أي بيانات'}), 400

        required_fields = ['name', 'email', 'subject', 'message']
        for field in required_fields:
            if not data.get(field):
                logger.error(f"Missing required field: {field}")
                return jsonify({'status': 'error', 'message': f'حقل {field} مطلوب'}), 400

        name = data['name']
        email = data['email']
        subject = data['subject']
        message = data['message']

        # التحقق من صحة البريد الإلكتروني
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            logger.error(f"Invalid email format: {email}")
            return jsonify({'status': 'error', 'message': 'صيغة البريد الإلكتروني غير صحيحة'}), 400

        # إنشاء محتوى الرسالة
        email_content = f"""
        رسالة جديدة من FileFlow:
        
        الاسم: {name}
        البريد الإلكتروني: {email}
        الموضوع: {subject}
        
        الرسالة:
        {message}
        """

        # إنشاء وإرسال البريد الإلكتروني
        msg = Message(
            subject=f'FileFlow رسالة جديدة: {subject}',
            recipients=['hamzaxnine@gmail.com'],
            body=email_content,
            reply_to=email
        )

        try:
            mail.send(msg)
            logger.info(f"Email sent successfully from {email}")
            return jsonify({'status': 'success', 'message': 'تم إرسال رسالتك بنجاح!'})
        except Exception as mail_error:
            logger.error(f"Error sending email: {str(mail_error)}")
            return jsonify({'status': 'error', 'message': 'حدث خطأ أثناء إرسال البريد الإلكتروني'}), 500

    except Exception as e:
        logger.error(f"Unexpected error in send_message: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'status': 'error', 'message': 'حدث خطأ غير متوقع'}), 500

@app.route('/api/contact', methods=['POST'])
def handle_contact():
    try:
        data = request.get_json()
        name = data.get('name')
        email = data.get('email')
        subject = data.get('subject')
        message = data.get('message')

        # Create email message
        msg = Message(
            subject=f"Contact Form: {subject}",
            recipients=[app.config['MAIL_USERNAME']],
            body=f"From: {name}\nEmail: {email}\n\nMessage:\n{message}"
        )

        # Send email
        mail.send(msg)

        return jsonify({
            'success': True,
            'message': 'تم إرسال رسالتك بنجاح'
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'حدث خطأ أثناء إرسال الرسالة'
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=port)
