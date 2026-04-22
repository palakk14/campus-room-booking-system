from flask import render_template, request, redirect, session, flash
from app import app
from db import get_db_connection
from security.security import (
    hash_password, verify_password,
    sanitize_input, is_valid_email, is_strong_password,
    generate_csrf_token, csrf_protect, rate_limit
)


@app.route('/')
def home():
    return render_template("index.html")


@app.route('/register', methods=['GET', 'POST'])
@rate_limit
def register():
    csrf_token = generate_csrf_token()

    if request.method == 'POST':
        # CSRF check
        if request.form.get("csrf_token") != session.get("csrf_token"):
            flash("Invalid request. Please try again.")
            return redirect('/register')

        name  = sanitize_input(request.form.get('name', ''))
        email = sanitize_input(request.form.get('email', ''))
        password = request.form.get('password', '')

        # Validation
        if not name or not email or not password:
            flash("All fields are required.")
            return redirect('/register')

        if not is_valid_email(email):
            flash("Please enter a valid email address.")
            return redirect('/register')

        valid_pw, pw_error = is_strong_password(password)
        if not valid_pw:
            flash(pw_error)
            return redirect('/register')

        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute("SELECT user_id FROM users WHERE email=%s", (email,))
            if cur.fetchone():
                flash("Email already registered.")
                return redirect('/register')

            hashed = hash_password(password)
            cur.execute(
                "INSERT INTO users(name, email, password, role) VALUES(%s,%s,%s,%s)",
                (name, email, hashed, 'user')
            )
            conn.commit()
            flash("Registration successful. Please login.")
            return redirect('/login')

        except Exception as e:
            conn.rollback()
            flash("Something went wrong during registration.")
            return redirect('/register')
        finally:
            cur.close()
            conn.close()

    return render_template("register.html", csrf_token=csrf_token)


@app.route('/login', methods=['GET', 'POST'])
@rate_limit
def login():
    csrf_token = generate_csrf_token()

    if request.method == 'POST':
        if request.form.get("csrf_token") != session.get("csrf_token"):
            flash("Invalid request. Please try again.")
            return redirect('/login')

        email    = sanitize_input(request.form.get('email', ''))
        password = request.form.get('password', '')

        if not email or not password:
            flash("Email and password are required.")
            return redirect('/login')

        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute("SELECT * FROM users WHERE email=%s", (email,))
            user = cur.fetchone()

            if user and verify_password(password, user['password']):
                session['user_id'] = user['user_id']
                session['name']    = user['name']
                session['role']    = user['role']

                if user['role'] == 'admin':
                    return redirect('/admin')
                return redirect('/dashboard')

            flash("Invalid email or password.")
            return redirect('/login')

        except Exception:
            flash("Something went wrong during login.")
            return redirect('/login')
        finally:
            cur.close()
            conn.close()

    return render_template("login.html", csrf_token=csrf_token)


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')
    return render_template("dashboard.html", name=session['name'])


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')
