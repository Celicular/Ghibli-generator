from flask import Flask, render_template, request, jsonify, session
from flask_socketio import SocketIO, emit
from werkzeug.utils import secure_filename
import os
from ghibli_image_generator import generate_ghibli_image
import base64
import uuid
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24).hex()
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Get Hugging Face token from environment
HF_TOKEN = os.getenv('HUGGING_FACE_TOKEN')
if not HF_TOKEN:
    raise ValueError("HUGGING_FACE_TOKEN environment variable is required")

socketio = SocketIO(app, cors_allowed_origins="*")

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def progress_callback(progress, client_id):
    """Send progress updates to the client via WebSocket"""
    socketio.emit('progress_update', {'progress': progress}, room=client_id)

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    session['client_id'] = request.sid

@app.route('/generate', methods=['POST'])
def generate():
    filepath = None
    try:
        client_id = request.form.get('client_id')
        if not client_id:
            return jsonify({'error': 'No client ID provided'}), 400

        if 'image' not in request.files or request.files['image'].filename == '':
            return jsonify({'error': 'No image selected'}), 400
        
        file = request.files['image']
        if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
            return jsonify({'error': 'Invalid file type. Please upload an image.'}), 400
        
        # Save and process the image
        filename = secure_filename(f"{uuid.uuid4()}_{file.filename}")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            result = generate_ghibli_image(
                prompt=request.form.get('prompt', "Ghibli Studio style, Charming hand-drawn anime-style illustration"),
                image_url=filepath,
                height=int(request.form.get('height', 768)),
                width=int(request.form.get('width', 768)),
                seed=int(request.form.get('seed', 42)),
                hf_token=HF_TOKEN,
                progress_callback=lambda p: progress_callback(p, client_id)
            )
            
            if not result:
                return jsonify({'error': 'Failed to generate image'}), 500
            
            # Process the result
            if isinstance(result, str):
                if os.path.isfile(result):
                    with open(result, 'rb') as img_file:
                        img_data = base64.b64encode(img_file.read()).decode()
                    return jsonify({'success': True, 'image': f'data:image/jpeg;base64,{img_data}'})
                return jsonify({'success': True, 'result': result})
            elif isinstance(result, dict) and 'image' in result:
                return jsonify({'success': True, 'image': result['image']})
            return jsonify({'success': True, 'result': result})
                
        except Exception as e:
            return jsonify({'error': str(e)}), 500
            
    except Exception as e:
        return jsonify({'error': 'Server error occurred'}), 500
        
    finally:
        if filepath and os.path.exists(filepath):
            try:
                os.remove(filepath)
            except:
                pass

if __name__ == '__main__':
    socketio.run(app, debug=True) 