from flask import render_template, redirect, request, url_for, flash
from . import auth
from flask_login import login_user, logout_user, login_required, current_user
from ..models import User,Permission
from .forms import LoginForm, RegistrationForm
from app import db
from ..email import send_mail

@auth.route('/login', methods=['GET','POST'])
def login():
    login_form = LoginForm()
    if login_form.validate_on_submit():
        user = User.query.filter_by(email=login_form.email.data).first()
        if user is not None and user.verify_password(login_form.password.data):
            login_user(user, login_form.remember_me.data)
            next = request.args.get('next')
            if next is None or not next.startswith('/'):
                next = url_for('main.index')
            return redirect(next)
        flash('Invalid Username or Password.')

    return render_template('auth/login.html',login_form=login_form,Permission=Permission)


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('main.index'))


@auth.route('/register',methods=['GET','POST'])
def register():
    reg_form = RegistrationForm()
    if reg_form.validate_on_submit():
        user = User(email=reg_form.email.data,
                    username=reg_form.username.data,
                    password=reg_form.password.data)
        
        db.session.add(user)
        db.session.commit()
        token = user.generate_confirmation_token()
        send_mail(user.email, 'Confirm your Account',
                      'auth/email/confirm',user=user,token=token)
        flash('A confirmation mail has been sent to you by mail.')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html',reg_form=reg_form,Permission=Permission)


@auth.route('/confirm/<token>')
@login_required
def confirm(token):
    if current_user.confirmed:
        return redirect(url_for('main.index'))
    if current_user.confirm(token):
        db.session.commit()
        flash('You have confirmed your account. Thanks!')

    else:
        flash('The confirmation link is invalid or has expired.')
    
    return redirect(url_for('main.index'))

@auth.before_app_request
def before_request():
    if current_user.is_authenticated:
        current_user.ping()
        if not current_user.confirmed and request.blueprint!='auth' and request.endpoint!='static':
            return redirect(url_for('auth.unconfirmed'))
    
@auth.route('/unconfirmed')
def unconfirmed():
    if current_user.is_anonymous or current_user.confirmed:
        return redirect(url_for('main.index'))
    return render_template('auth/unconfirmed.html',Permission=Permission)

@auth.route('/confirm')
@login_required
def resend_confirmation():
    token = current_user.generate_confirmation_token()
    send_mail(current_user.email, 'Confirm Your Account', 'auth/email/confirm',user=current_user,token=token)
    flash('A new confirmation email has been sent to you by email.')
    return redirect(url_for('main.index'))