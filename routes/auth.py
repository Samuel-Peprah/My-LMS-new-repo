# routes/auth.py (Updated)

from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from forms import LoginForm, RegistrationForm
from models import User
from extensions import db # Import db from extensions.py

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    current_year = datetime.utcnow().year
    if current_user.is_authenticated:
        return redirect(url_for('main.loading'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data, role='student')
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', title='Register', form=form, current_year=current_year)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    current_year = datetime.utcnow().year
    if current_user.is_authenticated:
        return redirect(url_for('main.loading'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password', 'danger')
            return redirect(url_for('auth.login'))
        login_user(user)
        next_page = request.args.get('next')
        return redirect(next_page or url_for('main.loading'))
    return render_template('auth/login.html', title='Sign In', form=form, current_year=current_year)

# @auth_bp.route('/logout')
# @login_required
# def logout():
#     logout_user()
#     flash('You have been logged out.', 'info')
#     return redirect(url_for('main.loading'))

@auth_bp.route('/logout')
@login_required
def logout():
    username = current_user.username  # store before logging out
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.loading', type='logout', username=username))
