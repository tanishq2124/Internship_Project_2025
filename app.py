import os
from flask import Flask, render_template, request, redirect, session, flash, url_for
from flask_mail import Mail, Message
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import Email, DataRequired, Length
from werkzeug.security import generate_password_hash, check_password_hash
import random
from flask_dance.contrib.google import make_google_blueprint, google
from smtplib import SMTPException

# The following line tells Flask-Dance to allow http for local development
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# ---------------------- Email Config ----------------------
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'tanishqparashar2@gmail.com'
app.config['MAIL_PASSWORD'] = 'frwytcnekntgpxgd'
app.config['MAIL_DEFAULT_SENDER'] = 'tanishqparashar2@gmail.com'
app.config['MAIL_DEBUG'] = True

mail = Mail(app)

# ---------------------- Google OAuth Config ----------------------
google_bp = make_google_blueprint(
    client_id="389441035592-flg658c4n7an50d80cr7qtoh4fslims2.apps.googleusercontent.com",
    client_secret="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",
    scope=["profile", "email"],
    redirect_to="google_dashboard"
)

# --- FIX: Explicitly set the scope to prevent it from being changed ---
google_bp.scope = [
    "https://www.googleapis.com/auth/userinfo.email",
    "openid",
    "https://www.googleapis.com/auth/userinfo.profile",
]

app.register_blueprint(google_bp, url_prefix="/login")


# ---------------------- Database Config ----------------------
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
db = SQLAlchemy(app)

# ---------------------- Models ----------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

# ---------------------- Forms ----------------------
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

# ---------------------- Routes ----------------------
@app.route('/')
def home():
    return redirect('/signin')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    form = SignUpForm()
    print("--- User is on the signup page ---")
    if form.validate_on_submit():
        print("--- Form was submitted and is valid ---")
        username = form.username.data
        email = form.email.data
        password = form.password.data

        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'warning')
            print("--- Email already registered ---")
            return redirect('/signup')

        otp = str(random.randint(100000, 999999))
        
        try:
            print(f"--- Attempting to send OTP to: {email} ---")
            msg = Message('OTP Verification', recipients=[email])
            msg.body = f'Your OTP is: {otp}'
            mail.send(msg)
            
            session['otp'] = otp
            session['email'] = email
            session['username'] = username
            session['password'] = generate_password_hash(password)
            
            flash('OTP sent to your email.', 'info')
            print("--- OTP sent successfully, redirecting to verify page ---")
            return redirect('/verify_otp')
        except SMTPException as e:
            flash('Failed to send OTP. Please check your email settings or try again later.', 'danger')
            print(f"--- SMTP Error: {e} ---")
            return redirect('/signup')
        except Exception as e:
            flash('An unexpected error occurred. Please try again.', 'danger')
            print(f"--- General Mail Error: {e} ---")
            return redirect('/signup')
    else:
        print("--- Form submission failed validation ---")
        for field, errors in form.errors.items():
            for error in errors:
                print(f"Validation error on {field}: {error}")
    return render_template('signup.html', form=form)

@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    form = OTPForm()
    if form.validate_on_submit():
        user_otp = form.otp.data
        session_otp = session.get('otp')
        email = session.get('email')
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

            flash('Account created successfully!', 'success')
            return redirect('/dashboard')
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

    user = User.query.filter_by(email=email).first()
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
    return redirect("/dashboard")


@app.route('/signin', methods=['GET', 'POST'])
def signin():
    form = SignInForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and check_password_hash(user.password, form.password.data):
            session['email'] = user.email
            return redirect('/dashboard')
        else:
            flash('Invalid email or password.', 'danger')
    return render_template('signin.html', form=form)

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        email = form.email.data
        user = User.query.filter_by(email=email).first()
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
            print(f"SMTP Error: {e}")
            return redirect('/forgot_password')
        except Exception as e:
            flash('An unexpected error occurred. Please try again.', 'danger')
            print(f"General Mail Error: {e}")
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
            user = User.query.filter_by(email=email).first()
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

@app.route('/dashboard')
def dashboard():
    if 'email' in session:
        user = User.query.filter_by(email=session['email']).first()
        return render_template("dashboard.html", user=user)
    return redirect('/signin')


@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect('/signin')

# ---------------------- Initialize DB ----------------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
