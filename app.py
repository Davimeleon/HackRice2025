# app.py
# Main Flask application for CloneMe - A dating app where users create AI clones that interact and match.

from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import json
from forms import RegistrationForm, LoginForm, CloneCreationForm
from models import init_db, User, Clone, Question, Answer
from llm import generate_conversation, calculate_compatibility, generate_persona 
import google.generativeai as genai
from PIL import Image

# Import from other modules
from models import init_db, User, Clone, Question, Answer  # Database models
from forms import RegistrationForm, LoginForm, CloneCreationForm  # WTForms for validation
from llm import generate_conversation, calculate_compatibility  # LLM helpers
from questions import DEFAULT_QUESTIONS  # Separate file for questions

app = Flask(__name__)
app.secret_key = 'super_secret_key'  # Change to a secure random key in production
app.config['UPLOAD_FOLDER'] = 'uploads'  # Folder for CSV uploads
app.config['ALLOWED_EXTENSIONS'] = {'txt', 'jpg', 'png', 'jpeg'}  # Allowed file types
app.config['APP_NAME'] = 'CloneMe'  # Define app name here

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize database
init_db()

# LLM Client (placeholder; configure with your API key)
genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.context_processor
def inject_app_name():
    return dict(app_name=app.config['APP_NAME'])  # Make app_name available to all templates

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        password_hash = generate_password_hash(password)
        
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', (username, password_hash))
            conn.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username already exists.', 'error')
        finally:
            conn.close()
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('SELECT id, password_hash FROM users WHERE username = ?', (username,))
        result = cursor.fetchone()
        conn.close()
        
        if result and check_password_hash(result[1], password):
            session['user_id'] = result[0]
            session['username'] = username
            flash('Login successful!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password.', 'error')
    return render_template('login.html', form=form)

@app.route('/home')
@app.route('/home')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, profile_pic_path FROM clones WHERE user_id = ?', (session['user_id'],))
    clone = cursor.fetchone()
    cursor.execute('SELECT username FROM users WHERE id = ?', (session['user_id'],))
    username = cursor.fetchone()[0]
    conn.close()
    has_clone = clone is not None
    profile_pic_path = clone[1] if clone and clone[1] else '/static/robot.png'
    print(f'Database profile_pic_path: {clone[1] if clone else None}')  # Debug
    # Normalize path and check existence
    if profile_pic_path and profile_pic_path != '/static/robot.png':
        profile_pic_path = profile_pic_path.replace('Uploads', 'uploads')
        absolute_path = os.path.join(app.root_path, profile_pic_path.lstrip('/'))
        if not os.path.exists(absolute_path):
            print(f'Image not found: {absolute_path}, using fallback')
            profile_pic_path = '/static/robot.png'
    print(f'Profile pic path: {profile_pic_path}')  # Debug
    return render_template('home.html', has_clone=has_clone, username=username, profile_pic_path=profile_pic_path)

@app.route('/create_clone', methods=['GET', 'POST'])
def create_clone():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    form = CloneCreationForm()
    form.questions = DEFAULT_QUESTIONS  # Attach questions for template rendering

    # Check if user has existing clone and pre-fill answers
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT answers_json, name FROM clones WHERE user_id = ?', (session['user_id'],))
    existing_clone = cursor.fetchone()
    conn.close()
    pre_filled_answers = json.loads(existing_clone[0]) if existing_clone else {}
    pre_filled_name = existing_clone[1] if existing_clone and existing_clone[1] is not None else ''
    
    print(f'Pre-filled name from database: {pre_filled_name}')  # Debug
    if request.method == 'GET':
        form.name.data = pre_filled_name
        print(f'Set form.name.data to: {form.name.data}')  # Debug
    for q in DEFAULT_QUESTIONS:
        if q['id'] in pre_filled_answers:
            setattr(form, q['id'], pre_filled_answers[q['id']])

    if form.validate_on_submit():
        try:
            # Collect answers, handling skips
            answers = {q['id']: request.form.get(q['id']) or None for q in DEFAULT_QUESTIONS}
            
            # Handle text file upload
            text_file = form.text_file.data  # Changed from csv_file
            text_path = None
            if text_file and allowed_file(text_file.filename):
                filename = secure_filename(text_file.filename)
                text_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                text_file.save(text_path)
            
            # Handle profile picture upload and composite with robot
            profile_pic_file = form.profile_pic.data
            profile_pic_path = None
            if profile_pic_file and allowed_file(profile_pic_file.filename):
                filename = secure_filename(profile_pic_file.filename)
                temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f"temp_{filename}")
                print(f'Saving temp file: {temp_path}')  # Debug
                profile_pic_file.save(temp_path)
            
                # Generate composite image
                try:
                    # Load images
                    print(f'Opening user image: {temp_path}')  # Debug
                    user_img = Image.open(temp_path).convert('RGBA')
                    print(f'Opening robot image: static/robot.png')  # Debug
                    robot_img = Image.open(os.path.join('static', 'robot.png')).convert('RGBA')
                    
                    # Resize user image to fit robot head (adjust size as needed)
                    head_size = (202, 167)  # Example size; adjust based on robot.png
                    user_img = user_img.resize(head_size, Image.Resampling.LANCZOS)
                    
                    # Define position for head (adjust x, y coordinates based on robot.png)
                    head_position = (187, 96)  # Example: top-left corner of head area
                    
                    # Create composite image
                    composite_img = robot_img.copy()
                    composite_img.paste(user_img, head_position, user_img)  # Use alpha channel for transparency
                    
                    # Save composite image
                    profile_pic_path = os.path.join(app.config['UPLOAD_FOLDER'], f"composite_{filename}")
                    absolute_path = os.path.join(app.root_path, profile_pic_path)
                    print(f'Saving composite image: {absolute_path}')  # Debug
                    composite_img.save(profile_pic_path, 'PNG')
                    print(f'Saved composite image: {absolute_path}')  # Debug
                    
                    # Clean up temporary file
                    print(f'Removing temp file: {temp_path}')  # Debug
                    os.remove(temp_path)
                except Exception as e:
                    flash(f'Error processing profile picture: {str(e)}', 'error')
                    print(f'Image processing error: {str(e)}')
                    profile_pic_path = None
            
            print(f'Final profile_pic_path: {profile_pic_path}')  # Debug

            # Generate persona using LLM
            try:
                persona = generate_persona(answers, text_path)
            except Exception as e:
                flash(f'Error generating persona: {str(e)}', 'error')
                persona = "Unable to generate persona due to API error."
            
            print("Generated Persona:")
            print(persona)

            # Save to database
            conn = sqlite3.connect('users.db')
            cursor = conn.cursor()
            # Delete existing clone if restarting
            cursor.execute('DELETE FROM clones WHERE user_id = ?', (session['user_id'],))
            cursor.execute('''
                INSERT INTO clones (user_id, answers_json, text_path, persona, profile_pic_path, name)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (session['user_id'], json.dumps(answers), text_path, persona, profile_pic_path, form.name.data))
            conn.commit()
            conn.close()
            
            flash('Clone created successfully!', 'success')
            return redirect(url_for('home'))
        except Exception as e:
            flash(f'Error creating clone: {str(e)}', 'error')
            print(f'Error in create_clone: {str(e)}')  # Debug to terminal
    else:
        print(f'Form validation failed: {form.errors}')  # Debug validation errors

    return render_template('create_clone.html', form=form, pre_filled_answers=pre_filled_answers, pre_filled_name=pre_filled_name)

@app.route('/date_clones')
def date_clones():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Fetch other clones (exclude user's own)
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT c.id, u.username, c.answers_json, c.persona, c.profile_pic_path 
        FROM clones c 
        JOIN users u ON c.user_id = u.id 
        WHERE c.user_id != ?
    ''', (session['user_id'],))
    other_clones = cursor.fetchall()
    
    # Fetch user's clone
    cursor.execute('SELECT answers_json, persona FROM clones WHERE user_id = ?', (session['user_id'],))
    user_clone = cursor.fetchone()
    conn.close()
    
    if not user_clone:
        flash('Create your clone first!', 'error')
        return redirect(url_for('create_clone'))
    
    user_answers = json.loads(user_clone[0])
    user_persona = user_clone[1]  # Fetch user's persona
    
    # Select 5 random clones (or all if fewer than 5)
    import random
    selected_clones = random.sample(other_clones, min(5, len(other_clones))) if other_clones else []
    
    clones_with_scores = []
    for clone_id, username, answers_json, other_persona, profile_pic_path in selected_clones:
        other_answers = json.loads(answers_json)
        score = calculate_compatibility(user_answers, other_answers)  # LLM-based score
        clones_with_scores.append({
            'id': clone_id,
            'username': username,
            'score': score,
            'profile_pic': profile_pic_path or '/static/default_profile.png'  # Fallback if none
        })
    
    return render_template('date_clones.html', clones=clones_with_scores)

@app.route('/view_match/<int:clone_id>')
def view_match(clone_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Fetch clones including personas
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT answers_json, persona FROM clones WHERE user_id = ?', (session['user_id'],))
    user_clone = cursor.fetchone()
    
    cursor.execute('SELECT answers_json, persona FROM clones WHERE id = ?', (clone_id,))
    other_clone = cursor.fetchone()
    
    # Fetch other username
    cursor.execute('SELECT u.username FROM clones c JOIN users u ON c.user_id = u.id WHERE c.id = ?', (clone_id,))
    other_username = cursor.fetchone()[0]
    conn.close()
    
    if not user_clone or not other_clone:
        flash('Clone not found.', 'error')
        return redirect(url_for('date_clones'))
    
    user_answers, user_persona, user_name = json.loads(user_clone[0]), user_clone[1], user_clone[2]
    other_answers, other_persona, other_name = json.loads(other_clone[0]), other_clone[1], other_clone[2]
    
    # Generate sample conversation using personas
    conversation = generate_conversation(user_answers, user_persona, other_answers, other_persona, user_name, other_name)
    
    # Replace 'Other:' with '{other_username}:'
    conversation = conversation.replace('Other:', f'{other_username}:')
    
    return render_template('view_match.html', conversation=conversation, other_username=other_username)

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('login'))

@app.route('/uploads/<path:filename>')
def serve_uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)