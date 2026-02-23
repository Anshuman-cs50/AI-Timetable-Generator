from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User
from app import db

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('main.manage'))
        else:
            flash('Login Unsuccessful. Please check username and password', 'danger')
    return render_template('login.html')

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
            return redirect(url_for('auth.register'))
        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('auth.login'))
    return render_template('register.html')

@auth.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.index'))

@auth.route('/demo-login')
def demo_login():
    # Find or create a demo user
    user = User.query.filter_by(username='demo_institution').first()
    if not user:
        user = User(username='demo_institution', is_demo=True)
        user.set_password('demo123')
        db.session.add(user)
        db.session.commit()
    login_user(user)
    flash('Logged in as Demo Institution', 'info')
    return redirect(url_for('main.manage'))
