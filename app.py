import os
import json
import re
from datetime import datetime
import random
from collections import defaultdict

from flask import Flask, render_template, request, redirect, session, flash, url_for, send_from_directory, jsonify
from flask_mail import Mail, Message
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import Email, DataRequired, Length, ValidationError
from flask_wtf.file import FileField
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_dance.contrib.google import make_google_blueprint, google
from smtplib import SMTPException
from sqlalchemy import select, desc 

# Enhanced AI libraries (optional)
try:
    import spacy
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    NLP_AVAILABLE = True
except ImportError:
    print("Warning: Advanced NLP libraries not installed. Using basic matching.")
    NLP_AVAILABLE = False

# The following line tells Flask-Dance to allow http for local development
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

app = Flask(__name__)
app.secret_key = 'your_secret_key' # Use a secure, complex secret key in production

# ---------------------- Global Config ----------------------
base_dir = os.path.abspath(os.path.dirname(__file__))
upload_folder = os.path.join(base_dir, 'static', 'profile_pics') 
app.config['UPLOAD_FOLDER'] = upload_folder
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# --- Template Directory Configuration ---
TEMPLATE_BASE_PATH = os.path.join(base_dir, 'templates', 'signup Signin')
os.makedirs(TEMPLATE_BASE_PATH, exist_ok=True)

# ---------------------- Enhanced AI Matching System ----------------------

class RequirementAnalyzer:
    def __init__(self):
        self.nlp = None
        if NLP_AVAILABLE:
            try:
                self.nlp = spacy.load("en_core_web_sm")
            except OSError:
                print("Warning: spaCy model not found. Using basic analysis.")
        
        self.page_types = ["login", "signup", "signin", "home", "dashboard", "about", "contact"]
        self.style_keywords = {
            "modern": ["modern", "sleek", "clean", "minimal", "contemporary"],
            "classic": ["classic", "traditional", "formal", "elegant"],
            "creative": ["creative", "artistic", "colorful", "unique", "vibrant"],
            "professional": ["professional", "corporate", "business", "formal"],
            "dark": ["dark", "night", "black", "shadow"],
            "cyberpunk": ["cyberpunk", "neon", "futuristic", "tech", "sci-fi"],
            "glassmorphism": ["glass", "blur", "transparent", "frosted"],
            "neumorphism": ["neumorphism", "soft", "subtle", "embossed"],
            "retro": ["retro", "vintage", "90s", "old-school"],
            "minimalist": ["minimalist", "simple", "bare", "basic"]
        }
        
        self.feature_keywords = {
            "social_login": ["social", "google", "facebook", "oauth", "third-party"],
            "forgot_password": ["forgot", "reset", "recover"],
            "remember_me": ["remember", "keep", "stay"],
            "animated": ["animated", "animation", "transition", "smooth"],
            "responsive": ["responsive", "mobile", "adaptive"],
            "single_form": ["single", "one", "only", "just"],
            "toggle": ["toggle", "switch", "tab", "flip"]
        }
        
        self.color_keywords = {
            "blue": ["blue", "azure", "navy", "cyan"],
            "red": ["red", "crimson", "scarlet"],
            "green": ["green", "emerald", "lime"],
            "purple": ["purple", "violet", "magenta"],
            "pink": ["pink", "rose", "coral"],
            "orange": ["orange", "amber"],
            "gradient": ["gradient", "rainbow", "multicolor"]
        }
        
    def analyze_prompt(self, user_prompt):
        """Enhanced analysis of user requirements"""
        doc = None
        if self.nlp:
            doc = self.nlp(user_prompt.lower())
        
        analysis = {
            "page_type": self.extract_page_type(user_prompt),
            "style_preference": self.extract_style(user_prompt),
            "color_preferences": self.extract_colors(user_prompt),
            "features": self.extract_features(user_prompt),
            "layout_preferences": self.extract_layout(user_prompt),
            "complexity": self.determine_complexity(user_prompt),
            "theme_intensity": self.determine_theme_intensity(user_prompt),
            "animation_preference": self.extract_animation_style(user_prompt),
            "single_form_request": self.is_single_form_request(user_prompt)
        }
        
        return analysis
    
    def extract_page_type(self, prompt):
        prompt_lower = prompt.lower()
        for page_type in self.page_types:
            if page_type in prompt_lower:
                return page_type
        return "login"  # default
    
    def extract_style(self, prompt):
        prompt_lower = prompt.lower()
        style_scores = {}
        
        for style, keywords in self.style_keywords.items():
            score = sum(1 for keyword in keywords if keyword in prompt_lower)
            if score > 0:
                style_scores[style] = score
        
        if style_scores:
            return max(style_scores, key=style_scores.get)
        return "modern"
    
    def extract_features(self, prompt):
        prompt_lower = prompt.lower()
        features = []
        
        for feature, keywords in self.feature_keywords.items():
            if any(keyword in prompt_lower for keyword in keywords):
                features.append(feature)
        
        return features
    
    def extract_colors(self, prompt):
        prompt_lower = prompt.lower()
        colors = []
        
        for color, keywords in self.color_keywords.items():
            if any(keyword in prompt_lower for keyword in keywords):
                colors.append(color)
        
        return colors
    
    def extract_layout(self, prompt):
        prompt_lower = prompt.lower()
        if any(word in prompt_lower for word in ["side by side", "horizontal", "split"]):
            return "horizontal"
        elif any(word in prompt_lower for word in ["vertical", "stack", "top bottom"]):
            return "vertical"
        return "default"
    
    def determine_complexity(self, prompt):
        prompt_lower = prompt.lower()
        complexity_indicators = {
            "simple": ["simple", "basic", "minimal", "clean"],
            "medium": ["modern", "professional", "standard"],
            "complex": ["advanced", "complex", "detailed", "rich", "interactive"]
        }
        
        for complexity, indicators in complexity_indicators.items():
            if any(indicator in prompt_lower for indicator in indicators):
                return complexity
        return "medium"
    
    def determine_theme_intensity(self, prompt):
        prompt_lower = prompt.lower()
        if any(word in prompt_lower for word in ["vibrant", "bright", "bold", "intense"]):
            return "high"
        elif any(word in prompt_lower for word in ["subtle", "soft", "gentle", "light"]):
            return "low"
        return "medium"
    
    def extract_animation_style(self, prompt):
        prompt_lower = prompt.lower()
        animation_styles = {
            "slide": ["slide", "sliding"],
            "flip": ["flip", "rotate", "3d"],
            "fade": ["fade", "opacity"],
            "scale": ["scale", "zoom", "grow"]
        }
        
        for style, keywords in animation_styles.items():
            if any(keyword in prompt_lower for keyword in keywords):
                return style
        return "slide"  # default
    
    def is_single_form_request(self, prompt):
        prompt_lower = prompt.lower()
        return any(phrase in prompt_lower for phrase in [
            "only signup", "only signin", "only login", "single form", "just signup", "just signin"
        ])

class EnhancedTemplateMatchingEngine:
    def __init__(self):
        self.templates_metadata = self.load_enhanced_templates_metadata()
        self.vectorizer = TfidfVectorizer() if NLP_AVAILABLE else None
        
    def load_enhanced_templates_metadata(self):
        """Load and enhance template metadata with detailed analysis"""
        details_path = os.path.join(TEMPLATE_BASE_PATH, 'details.txt')
        templates = {}
        
        try:
            with open(details_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            sections = content.split('_______________________________________________________________________________________')
            
            for section in sections:
                section = section.strip()
                if section.startswith('(') and section.find(').') != -1:
                    try:
                        index_end = section.find(').')
                        template_id = int(section[1:index_end].strip())
                        prompt_text = section[index_end + 2:].strip()
                        
                        # Enhanced metadata extraction
                        templates[template_id] = {
                            'description': prompt_text,
                            'analyzed_requirements': self.analyze_template_features(prompt_text),
                            'difficulty_level': self.assess_template_difficulty(prompt_text),
                            'primary_theme': self.extract_primary_theme(prompt_text),
                            'supported_features': self.extract_supported_features(prompt_text)
                        }
                    except ValueError:
                        continue
                        
        except FileNotFoundError:
            print(f"Warning: {details_path} not found. Using minimal fallback data.")
            templates = {
                1: {
                    'description': "Create a responsive login and signup form with toggle",
                    'analyzed_requirements': {'style': 'modern', 'features': ['toggle', 'responsive']},
                    'difficulty_level': 'medium',
                    'primary_theme': 'modern',
                    'supported_features': ['login', 'signup', 'toggle']
                }
            }
        
        return templates
    
    def analyze_template_features(self, description):
        """Analyze what features each template offers"""
        analyzer = RequirementAnalyzer()
        return analyzer.analyze_prompt(description)
    
    def assess_template_difficulty(self, description):
        """Assess complexity level of template"""
        desc_lower = description.lower()
        if any(word in desc_lower for word in ["advanced", "complex", "3d", "animated"]):
            return "high"
        elif any(word in desc_lower for word in ["simple", "basic", "minimal"]):
            return "low"
        return "medium"
    
    def extract_primary_theme(self, description):
        """Extract the main visual theme"""
        desc_lower = description.lower()
        themes = {
            "dark": ["dark", "night", "black"],
            "cyberpunk": ["cyberpunk", "neon", "futuristic"],
            "glass": ["glass", "blur", "transparent"],
            "minimal": ["minimal", "clean", "simple"],
            "retro": ["retro", "90s", "vintage"]
        }
        
        for theme, keywords in themes.items():
            if any(keyword in desc_lower for keyword in keywords):
                return theme
        return "modern"
    
    def extract_supported_features(self, description):
        """Extract what features this template supports"""
        desc_lower = description.lower()
        features = []
        
        feature_map = {
            "social_login": ["social", "google", "facebook"],
            "animations": ["animated", "animation", "transition"],
            "responsive": ["responsive", "mobile"],
            "toggle": ["toggle", "switch", "flip"],
            "forgot_password": ["forgot", "reset"],
            "dark_mode": ["dark", "night"]
        }
        
        for feature, keywords in feature_map.items():
            if any(keyword in desc_lower for keyword in keywords):
                features.append(feature)
                
        return features
    
    def find_best_match(self, requirements):
        """Enhanced matching algorithm with multiple criteria"""
        scores = []
        
        for template_id, template_data in self.templates_metadata.items():
            score = self.calculate_enhanced_similarity_score(requirements, template_data)
            scores.append((template_id, template_data, score))
        
        # Sort by score (highest first)
        scores.sort(key=lambda x: x[2], reverse=True)
        
        best_match = scores[0]
        
        # Dynamic thresholds based on requirements complexity
        high_threshold = 0.8 if requirements.get('complexity') == 'complex' else 0.7
        medium_threshold = 0.5 if requirements.get('complexity') == 'simple' else 0.4
        
        if best_match[2] >= high_threshold:
            return "exact_match", best_match[0], best_match[1], best_match[2]
        elif best_match[2] >= medium_threshold:
            return "partial_match", best_match[0], best_match[1], best_match[2]
        else:
            return "no_match", None, None, 0
    
    def calculate_enhanced_similarity_score(self, requirements, template_data):
        """Enhanced scoring with weighted criteria"""
        score = 0
        total_weight = 0
        
        template_req = template_data.get('analyzed_requirements', {})
        
        # Style matching (weight: 0.25)
        if requirements.get('style_preference') == template_req.get('style_preference'):
            score += 0.25
        elif self.styles_compatible(requirements.get('style_preference'), template_req.get('style_preference')):
            score += 0.15
        total_weight += 0.25
        
        # Feature matching (weight: 0.3)
        req_features = set(requirements.get('features', []))
        template_features = set(template_data.get('supported_features', []))
        
        if req_features and template_features:
            feature_overlap = len(req_features & template_features)
            feature_union = len(req_features | template_features)
            if feature_union > 0:
                feature_score = feature_overlap / feature_union
                score += 0.3 * feature_score
        total_weight += 0.3
        
        # Theme matching (weight: 0.2)
        if requirements.get('style_preference') == template_data.get('primary_theme'):
            score += 0.2
        total_weight += 0.2
        
        # Complexity compatibility (weight: 0.15)
        req_complexity = requirements.get('complexity', 'medium')
        template_difficulty = template_data.get('difficulty_level', 'medium')
        
        complexity_compatibility = {
            ('simple', 'low'): 1.0,
            ('simple', 'medium'): 0.8,
            ('medium', 'medium'): 1.0,
            ('medium', 'high'): 0.7,
            ('complex', 'high'): 1.0,
            ('complex', 'medium'): 0.8
        }
        
        compat_score = complexity_compatibility.get((req_complexity, template_difficulty), 0.5)
        score += 0.15 * compat_score
        total_weight += 0.15
        
        # Special handling for single form requests (weight: 0.1)
        if requirements.get('single_form_request'):
            if 'single' in template_data.get('description', '').lower():
                score += 0.1
        total_weight += 0.1
        
        return score / total_weight if total_weight > 0 else 0
    
    def styles_compatible(self, style1, style2):
        """Check if two styles are compatible"""
        compatible_groups = [
            {'modern', 'minimal', 'clean'},
            {'dark', 'cyberpunk', 'tech'},
            {'glass', 'modern', 'blur'},
            {'retro', 'vintage', 'colorful'}
        ]
        
        if not style1 or not style2:
            return False
            
        for group in compatible_groups:
            if style1 in group and style2 in group:
                return True
        return False

# --- Legacy Simple Matching for backwards compatibility ---
SEARCHABLE_TOKENS = {
    'dark', 'neon', 'cyberpunk', 'minimalist', 'vibrant', 'gradient', 'glassmorphism', 
    'pastel', 'retro', '90s', 'professional', 'light', 'clean',
    'signup', 'signin', 'login', 'forms', 'single', 'only', 
    'slide', 'flip', '3d', 'rotate', 'tab', 'animated', 
    'social', 'icons', 'responsive', 'ecommerce', 'dashboard'
}

def load_template_data():
    """Legacy function - kept for backwards compatibility"""
    details_path = os.path.join(TEMPLATE_BASE_PATH, 'details.txt')
    raw_template_data = {}
    template_data = {}
    
    try:
        with open(details_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        
        sections = content.split('_______________________________________________________________________________________')
        
        for section in sections:
            section = section.strip()
            if section.startswith('(') and section.find(').') != -1:
                try:
                    index_end = section.find(').')
                    template_id = int(section[1:index_end].strip())
                    prompt_text = section[index_end + 2:].strip()
                    raw_template_data[template_id] = prompt_text
                except ValueError:
                    continue
            
    except FileNotFoundError:
        print(f"Error: {details_path} not found. Using fallback data.")
        raw_template_data = {
            1: "(1) Create a responsive login and signup form with a toggle. Modern, clean design.",
            14: "(14) Dark Cyberpunk theme, high contrast, electric blue, neon pink, 3D perspective rotation."
        }
    
    # Tokenize the prompt text to create a feature set
    for template_id, prompt_text in raw_template_data.items():
        template_data[template_id] = {
            'description': prompt_text,
            'features': set(word for word in prompt_text.lower().split() if word in SEARCHABLE_TOKENS)
        }
    
    return template_data

TEMPLATE_DATA = load_template_data()

def find_best_match(user_prompt: str, templates: dict) -> int:
    """Legacy function - kept for backwards compatibility"""
    user_prompt_lower = user_prompt.lower()
    user_prompt_features = set(word for word in user_prompt_lower.split() if word in SEARCHABLE_TOKENS)
    
    if not user_prompt_features:
        return 1 # Fallback

    best_match_id = 1
    max_score = -1
    
    for template_id, data in templates.items():
        template_features = data['features']
        
        score = len(user_prompt_features.intersection(template_features))
        
        # Bonus for high-impact multi-word matches
        if 'dark theme' in user_prompt_lower and 'dark' in template_features:
            score += 2
        if 'social media' in user_prompt_lower and 'social' in template_features:
            score += 2

        if score > max_score:
            max_score = score
            best_match_id = template_id
            
    return best_match_id

# ---------------------- Email, OAuth, DB Config and Models ----------------------

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'tanishqparashar2@gmail.com'
app.config['MAIL_PASSWORD'] = 'frwytcnekntgpxgd'
app.config['MAIL_DEFAULT_SENDER'] = 'tanishqparashar2@gmail.com'
app.config['MAIL_DEBUG'] = True
mail = Mail(app)

google_bp = make_google_blueprint(
    client_id="389441035592-flg658c4n7an50d80cr7qtoh4fslims2.apps.googleusercontent.com",
    client_secret="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", 
    scope=["profile", "email"],
    redirect_to="google_dashboard"
)
google_bp.scope = [
    "https://www.googleapis.com/auth/userinfo.email",
    "openid",
    "https://www.googleapis.com/auth/userinfo.profile",
]
app.register_blueprint(google_bp, url_prefix="/login")

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    profile_image = db.Column(db.String(200), default='default.png')

class SearchHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    query = db.Column(db.String(500), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    match_score = db.Column(db.Float, default=0.0)
    template_used = db.Column(db.Integer, default=1)
    generation_type = db.Column(db.String(50), default='template_match')
    user = db.relationship('User', backref=db.backref('search_history', lazy=True))

# --- FORMS ---
class SignUpForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=30)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('Sign Up')

class SignInForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Sign In')

class OTPForm(FlaskForm):
    otp = StringField('Enter OTP', validators=[DataRequired(), Length(min=6, max=6)])
    submit = SubmitField('Verify')

class ForgotPasswordForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Send OTP')

class ResetPasswordForm(FlaskForm):
    otp = StringField('OTP', validators=[DataRequired(), Length(min=6, max=6)])
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('Reset Password')

class EditProfileForm(FlaskForm):
    username = StringField('New Username', validators=[DataRequired(), Length(min=3, max=30)])
    new_password = PasswordField('New Password (Leave blank to keep old)', validators=[Length(max=50)])
    profile_image = FileField('Upload Profile Picture') 
    submit = SubmitField('Save Changes')

# ---------------------- Helper Functions ----------------------
def allowed_file(filename):
    """Checks if the file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
           
def validate_image(form, field):
    """Custom WTForms validator to check file type/extension."""
    if field.data:
        if hasattr(field.data, 'filename'):
            filename = field.data.filename
            if not allowed_file(filename):
                raise ValidationError(
                    'Invalid file extension. Allowed types: png, jpg, jpeg, gif.'
                )

def get_user_by_email(email):
    stmt = select(User).filter_by(email=email)
    return db.session.scalars(stmt).first()

# ---------------------- Main AI Generation System ----------------------
class WebsiteGenerator:
    def __init__(self):
        self.analyzer = RequirementAnalyzer()
        self.matcher = EnhancedTemplateMatchingEngine()
    
    def process_user_request(self, user_prompt):
        # Step 1: Analyze user requirements
        requirements = self.analyzer.analyze_prompt(user_prompt)
        
        # Step 2: Find best matching template
        match_type, template_id, template_data, match_score = self.matcher.find_best_match(requirements)
        
        # Step 3: Determine action taken
        if match_type == "exact_match":
            action_taken = f"Perfect match found! Using Template {template_id} (Confidence: {match_score:.2f})"
        elif match_type == "partial_match":
            action_taken = f"Good match found! Using Template {template_id} with AI customizations (Confidence: {match_score:.2f})"
        else:  # no_match
            # Fallback to legacy matching
            template_id = find_best_match(user_prompt, TEMPLATE_DATA)
            match_score = 0.65  # Default confidence for legacy matching
            action_taken = f"Using Template {template_id} with basic matching"
        
        return {
            'template_id': template_id,
            'match_score': match_score,
            'requirements': requirements,
            'action_taken': action_taken
        }

# ---------------------- Routes ----------------------

@app.route('/')
def home():
    # Redirects to signup if not authenticated, otherwise to index
    if 'email' in session:
        return redirect(url_for('index'))
    return redirect('/signup')

@app.route('/index')
def index():
    """Main dashboard page - only accessible after login"""
    if 'email' not in session:
        return redirect('/signin')
    
    user = get_user_by_email(session['email'])
    return render_template("index.html", user=user)

@app.route('/generate', methods=['POST'])
def generate():
    """Handle generation request from index.html search form"""
    if 'email' not in session:
        return redirect('/signin')

    user = get_user_by_email(session['email'])
    query = request.form.get('query', '').strip()

    if not query or not user:
         flash('Please enter a description to generate a website.', 'warning')
         return redirect(url_for('index'))

    # Use enhanced AI system
    try:
        generator = WebsiteGenerator()
        result = generator.process_user_request(query)
        
        # Store in search history
        new_history = SearchHistory(
            user_id=user.id, 
            query=query,
            match_score=result['match_score'],
            template_used=result['template_id'],
            generation_type='ai_enhanced'
        )
        db.session.add(new_history)
        db.session.commit()
        
        flash(f'Website generated successfully! {result["action_taken"]}', 'success')
        
        return redirect(url_for('dashboard', 
                               template_id=result['template_id'], 
                               query=query, 
                               score=result['match_score']))
        
    except Exception as e:
        # Fallback to legacy system
        template_id = find_best_match(query, TEMPLATE_DATA)
        
        new_history = SearchHistory(user_id=user.id, query=query)
        db.session.add(new_history)
        db.session.commit()
        
        flash(f'Website generation matched to Template {template_id}!', 'success')
        return redirect(url_for('dashboard', template_id=template_id, query=query))

@app.route('/dashboard')
def dashboard():
    """Enhanced dashboard showing AI results"""
    if 'email' not in session:
        return redirect('/signin')
    
    template_id = request.args.get('template_id', 1, type=int)
    user_query = request.args.get('query', 'Generated website')
    match_score = request.args.get('score', 0.85, type=float)
    
    # Get template description
    template_description = TEMPLATE_DATA.get(template_id, {}).get('description', 'AI Generated Website')
    
    return render_template('dashboard.html',
                         template_id=template_id,
                         user_prompt=user_query,
                         generated_prompt=template_description,
                         match_score=match_score,
                         template_name=f"Template {template_id}")

# ---------------------- Legacy AI Edit Route (Preserved) ----------------------
@app.route('/ai_edit_result')
def ai_edit_result():
    """Legacy route - preserved for backwards compatibility"""
    if 'email' not in session:
        return redirect(url_for('signin'))
    
    user_query = session.pop('ai_edit_query', "AI Generated Single Form.")
    base_id = session.pop('ai_edit_base_id', 1) 
    target_form = session.pop('ai_edit_target', 'signup').capitalize()
    
    is_dark = base_id in [8, 14, 7] # 7 (Glass), 8/14 (Dark/Cyber) are dark/themed
    
    if is_dark:
        theme_bg = "#1a1a2e"
        theme_card = "#2a2a44"
        theme_accent = "#ff0077"
        theme_primary = "#00bcd4"
        theme_desc = f"AI Edited from Template {base_id} (Dark/Themed Component)"
        text_color = "#e9e4f0"
    else:
        theme_bg = "#f0f0f0"
        theme_card = "#ffffff"
        theme_accent = "#764ba2"
        theme_primary = "#1a202c"
        theme_desc = f"AI Edited from Template {base_id} (Default/Light Component)"
        text_color = "#1a202c"

    # Hardcoded backup HTML generation
    simulated_html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>AI Refined {target_form}</title>
    <style>
        body {{
            background-color: {theme_bg};
            color: {text_color};
            font-family: Arial, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
        }}
        .form-container {{
            background: {theme_card}; 
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4);
            padding: 40px;
            width: 380px;
            text-align: center;
        }}
        .form-container h1 {{
            color: {theme_accent};
            margin-bottom: 30px;
            font-size: 2.2em;
        }}
        input {{
            width: 100%;
            padding: 12px;
            margin: 10px 0;
            border: 1px solid {theme_primary};
            background: {theme_bg if is_dark else '#f7f7f7'};
            color: {text_color};
            border-radius: 5px;
            box-sizing: border-box;
        }}
        button {{
            width: 100%;
            padding: 15px;
            background: {theme_accent};
            border: none;
            color: white;
            font-weight: bold;
            border-radius: 25px;
            margin-top: 25px;
            cursor: pointer;
        }}
    </style>
</head>
<body>
    <div class="form-container">
        <h1>{target_form}</h1>
        <form>
            <input type="email" placeholder="Email" required />
            <input type="password" placeholder="Password" required />
            {'<input type="text" placeholder="Username" required />' if target_form == 'Signup' else ''}
            <button type="submit">{target_form.upper()}</button>
        </form>
        <p style="margin-top: 20px; font-size: 0.9em;">Powered by Website Buddy AI</p>
    </div>
</body>
</html>
"""
    
    return render_template(
        "dashboard.html", 
        user_prompt=user_query, 
        template_id=999, 
        template_name=f"ai_edited_{target_form.lower()}.html",
        generated_prompt=theme_desc,
        match_score=0.95
    )

# ---------------------- Template Serving Routes ----------------------
@app.route('/template_file/<int:template_id>')
def serve_template_file(template_id):
    """Serves the raw HTML content for templates with enhanced fallback"""
    file_name = f"{template_id}.html"
    
    try:
        return send_from_directory(
            directory=TEMPLATE_BASE_PATH, 
            path=file_name,
            mimetype='text/html'
        )
    except FileNotFoundError:
        # Enhanced fallback for missing templates
        fallback_html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Generated Website - Template {template_id}</title>
    <style>
        body {{
            font-family: 'Inter', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0;
            color: white;
        }}
        .container {{
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 50px;
            text-align: center;
            max-width: 500px;
            border: 1px solid rgba(255, 255, 255, 0.2);
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
        }}
        h1 {{
            font-size: 2.5rem;
            margin-bottom: 20px;
            text-shadow: 0 0 20px rgba(0, 188, 212, 0.5);
        }}
        p {{
            font-size: 1.1rem;
            margin-bottom: 30px;
            opacity: 0.9;
        }}
        .form {{
            text-align: left;
        }}
        input {{
            width: 100%;
            padding: 15px;
            margin: 10px 0;
            border: 1px solid rgba(0, 188, 212, 0.5);
            background: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            color: white;
            font-size: 16px;
        }}
        input::placeholder {{
            color: rgba(255, 255, 255, 0.7);
        }}
        button {{
            width: 100%;
            padding: 15px;
            background: linear-gradient(45deg, #00bcd4, #ff0077);
            border: none;
            border-radius: 10px;
            color: white;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            margin-top: 20px;
            transition: transform 0.3s;
        }}
        button:hover {{
            transform: translateY(-2px);
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 AI Generated</h1>
        <p>Template {template_id} - Enhanced with AI matching</p>
        <div class="form">
            <input type="email" placeholder="Email Address" />
            <input type="password" placeholder="Password" />
            <button>Sign In</button>
        </div>
        <p style="margin-top: 30px; font-size: 0.9em; opacity: 0.7;">
            Generated by WebBuddy AI
        </p>
    </div>
</body>
</html>
        """
        from flask import Response
        return Response(fallback_html, mimetype='text/html')

# ---------------------- Enhanced Results Route ----------------------
@app.route('/enhanced_results')
def enhanced_results():
    """Display enhanced AI generation results"""
    if 'email' not in session:
        return redirect(url_for('signin'))
    
    # This would be used if you have the enhanced_results.html template
    result = session.get('generation_result')
    if not result:
        flash('No generation result found.', 'warning')
        return redirect(url_for('index'))
    
    return render_template('enhanced_results.html', **result)

# ---------------------- Standard Auth Routes (All Preserved) ----------------------

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    form = SignUpForm()
    if form.validate_on_submit():
        username = form.username.data
        email = form.email.data
        password = form.password.data

        if get_user_by_email(email): 
            flash('Email already registered.', 'warning')
            return redirect('/signup')

        otp = str(random.randint(100000, 999999))
        
        try:
            msg = Message('OTP Verification', recipients=[email])
            msg.body = f'Your OTP is: {otp}'
            mail.send(msg)
            
            session['otp'] = otp
            session['email_temp'] = email 
            session['username'] = username
            session['password'] = generate_password_hash(password)
            
            flash('OTP sent to your email.', 'info')
            return redirect('/verify_otp')
        except SMTPException as e:
            flash('Failed to send OTP. Please check your email settings or try again later.', 'danger')
            return redirect('/signup')
        except Exception as e:
            flash('An unexpected error occurred. Please try again.', 'danger')
            return redirect('/signup')
    return render_template('signup.html', form=form)

@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    form = OTPForm()
    if form.validate_on_submit():
        user_otp = form.otp.data
        session_otp = session.get('otp')
        email = session.get('email_temp')
        username = session.get('username')
        password = session.get('password')

        if user_otp == session_otp and email and password and username:
            new_user = User(email=email, username=username, password=password)
            db.session.add(new_user)
            db.session.commit()

            session['email'] = new_user.email
            session.pop('otp', None)
            session.pop('password', None)
            session.pop('username', None)
            session.pop('email_temp', None)

            flash('Account created successfully!', 'success')
            return redirect('/index')
        else:
            flash('Invalid OTP.', 'danger')
    return render_template('verify_otp.html', form=form)

@app.route("/google_dashboard")
def google_dashboard():
    if not google.authorized:
        return redirect(url_for("google.login"))

    resp = google.get("/oauth2/v2/userinfo")
    if not resp.ok:
        flash("Failed to fetch user info from Google.", "danger")
        return redirect("/signin")

    user_info = resp.json()
    email = user_info["email"]
    name = user_info.get("name", email.split("@")[0])

    user = get_user_by_email(email) 
    if not user:
        user = User(
            username=name,
            email=email,
            password=generate_password_hash(str(random.randint(100000, 999999)))
        )
        db.session.add(user)
        db.session.commit()

    session["email"] = user.email
    flash(f"Welcome {name}, signed in with Google!", "success")
    return redirect("/index")

@app.route('/signin', methods=['GET', 'POST'])
def signin():
    form = SignInForm()
    if form.validate_on_submit():
        user = get_user_by_email(form.email.data) 
        if user and check_password_hash(user.password, form.password.data):
            session['email'] = user.email
            return redirect('/index')
        else:
            flash('Invalid email or password.', 'danger')
    return render_template('signin.html', form=form)

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        email = form.email.data
        user = get_user_by_email(email) 
        if not user:
            flash('No account with that email.', 'warning')
            return redirect('/forgot_password')

        otp = str(random.randint(100000, 999999))
        
        try:
            msg = Message('Reset Password OTP', recipients=[email])
            msg.body = f'Your OTP to reset password is: {otp}'
            mail.send(msg)
            
            session['reset_email'] = email
            session['reset_otp'] = otp
            
            flash('OTP sent to your email.', 'info')
            return redirect('/reset_password')
        except SMTPException as e:
            flash('Failed to send OTP. Please try again later.', 'danger')
            return redirect('/forgot_password')
        except Exception as e:
            flash('An unexpected error occurred. Please try again.', 'danger')
            return redirect('/forgot_password')

    return render_template('forgot_password.html', form=form)

@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    form = ResetPasswordForm()
    if form.validate_on_submit():
        otp = form.otp.data
        new_password = form.new_password.data
        session_otp = session.get('reset_otp')
        email = session.get('reset_email')

        if otp == session_otp and email:
            user = get_user_by_email(email) 
            if user:
                user.password = generate_password_hash(new_password)
                db.session.commit()

            session.pop('reset_otp', None)
            session.pop('reset_email', None)

            flash('Password reset successfully.', 'success')
            return redirect('/signin')
        else:
            flash('Invalid OTP or session expired.', 'danger')
    return render_template('reset_password.html', form=form)

@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if 'email' not in session:
        return '<p>Unauthorized</p>', 401 
    
    user = get_user_by_email(session['email']) 
    form = EditProfileForm()
    
    if form.validate_on_submit():
        user.username = form.username.data
        if form.new_password.data:
            user.password = generate_password_hash(form.new_password.data)
        if form.profile_image.data:
            file = form.profile_image.data
            if file and allowed_file(file.filename):
                extension = file.filename.rsplit('.', 1)[1].lower()
                unique_filename = f'{user.id}_{secure_filename(user.username)}_{datetime.now().strftime("%Y%m%d%H%M%S")}.{extension}'
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                try:
                    file.save(file_path)
                    user.profile_image = unique_filename
                except Exception as e:
                    flash(f'Error saving image: {e}', 'danger')
                    db.session.rollback()
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('index'))
    elif request.method == 'GET':
        form.username.data = user.username
        
    return render_template('edit_profile_modal.html', form=form, user=user)

@app.route('/history')
def view_history():
    if 'email' not in session:
        return redirect('/signin')
    user = get_user_by_email(session['email']) 
    stmt = select(SearchHistory).filter_by(user_id=user.id).order_by(desc(SearchHistory.timestamp))
    history = db.session.scalars(stmt).all()
    return render_template('history.html', history=history, user=user)

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect('/signin')

# ---------------------- API Routes ----------------------
@app.route('/api/analyze_prompt', methods=['POST'])
def analyze_prompt():
    """API endpoint to analyze user prompt and return requirements"""
    data = request.get_json()
    prompt = data.get('prompt', '')
    
    if not prompt:
        return jsonify({'error': 'No prompt provided'}), 400
    
    try:
        analyzer = RequirementAnalyzer()
        requirements = analyzer.analyze_prompt(prompt)
        
        return jsonify({
            'requirements': requirements,
            'confidence': 0.85
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/clear_history', methods=['POST'])
def clear_history():
    """Clear user's search history"""
    if 'email' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    user = get_user_by_email(session['email'])
    SearchHistory.query.filter_by(user_id=user.id).delete()
    db.session.commit()
    
    return jsonify({'success': True})

# ---------------------- Legacy Routes for Backwards Compatibility ----------------------
@app.route('/dashboard', methods=['GET', 'POST'])
def legacy_dashboard():
    """Legacy dashboard route - redirects to appropriate page"""
    if 'email' not in session:
        return redirect('/signin')
    
    # If it's a POST request, handle like the old system
    if request.method == 'POST':
        return generate()  # Use the new generate function
    
    # If it's a GET request, show dashboard
    return dashboard()

@app.route('/generate_result/<int:template_id>', methods=['GET'])
def template_results(template_id):
    """Legacy route for backward compatibility"""
    return redirect(url_for('dashboard', template_id=template_id))

# ---------------------- Initialize DB ----------------------
if __name__ == "__main__":
    with app.app_context():
        os.makedirs(upload_folder, exist_ok=True)
        os.makedirs(TEMPLATE_BASE_PATH, exist_ok=True) 
        try:
            db.create_all() 
        except Exception as e:
            print(f"Database initialization failed: {e}. Check your models and database file.")
    app.run(debug=True)