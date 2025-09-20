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

# Import from other modules
from models import init_db, User, Clone, Question, Answer  # Database models
from forms import RegistrationForm, LoginForm, CloneCreationForm  # WTForms for validation
from llm import generate_conversation, calculate_compatibility  # LLM helpers
from questions import DEFAULT_QUESTIONS  # Separate file for questions

app = Flask(__name__)
app.secret_key = 'super_secret_key'  # Change to a secure random key in production
app.config['UPLOAD_FOLDER'] = 'uploads'  # Folder for CSV uploads
app.config['ALLOWED_EXTENSIONS'] = {'txt'}  # Allowed file types
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
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('home.html')

@app.route('/create_clone', methods=['GET', 'POST'])
def create_clone():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    form = CloneCreationForm()
    form.questions = DEFAULT_QUESTIONS  # Attach questions for template rendering
    
    if form.validate_on_submit():
        # Collect answers, handling skips
        answers = {q['id']: request.form.get(q['id']) or None for q in DEFAULT_QUESTIONS}
        
        # Handle text file upload
        text_file = form.text_file.data  # Changed from csv_file
        text_path = None
        if text_file and allowed_file(text_file.filename):
            filename = secure_filename(text_file.filename)
            text_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            text_file.save(text_path)
        
        # Generate persona using LLM
        persona = generate_persona(answers, text_path)
        
        # Generate sample conversation (simplified; uses personas if available, but for initial clone, use basic prompt)
        conversation_prompt = "Simulate a sample conversation for a new dating clone based on their profile."
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            llm_response = model.generate_content(conversation_prompt).text
        except Exception as e:
            flash(f'Error generating LLM conversation: {str(e)}', 'error')
            llm_response = "Unable to generate conversation due to API error."
        
        print("Generated Persona:")
        print(persona)
        print("\nSample Conversation:")
        print(llm_response)

        # Save to database
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO clones (user_id, answers_json, text_path, llm_conversation, persona)
            VALUES (?, ?, ?, ?, ?)
        ''', (session['user_id'], json.dumps(answers), text_path, llm_response, persona))
        conn.commit()
        conn.close()
        
        flash('Clone created successfully!', 'success')
        return redirect(url_for('home'))
    
    return render_template('create_clone.html', form=form)

@app.route('/date_clones')
def date_clones():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Fetch other clones (exclude user's own)
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT c.id, u.username, c.answers_json, c.persona 
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
    for clone_id, username, answers_json, other_persona in selected_clones:
        other_answers = json.loads(answers_json)
        score = calculate_compatibility(user_answers, other_answers)  # LLM-based score
        clones_with_scores.append({
            'id': clone_id,
            'username': username,
            'score': score,
            'profile_pic': '/static/default_profile.png'  # Placeholder; add real upload later
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
    conn.close()
    
    if not user_clone or not other_clone:
        flash('Clone not found.', 'error')
        return redirect(url_for('date_clones'))
    
    user_answers, user_persona = json.loads(user_clone[0]), user_clone[1]
    other_answers, other_persona = json.loads(other_clone[0]), other_clone[1]
    
    # Generate sample conversation using personas
    conversation = generate_conversation(user_answers, user_persona, other_answers, other_persona)
    
    return render_template('view_match.html', conversation=conversation)

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)