import re

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from db_settings import db, people

auth = Blueprint('auth', __name__, template_folder='../templates/auth')

_PHONE_RE = re.compile(r'^\+?[0-9\s\-()]{10,18}$')


def _normalize_phone(phone):
    digits = re.sub(r'\D', '', phone or '')
    if digits.startswith('8') and len(digits) == 11:
        digits = '7' + digits[1:]
    return digits


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('portal.dashboard'))

    if request.method == 'POST':
        phone = _normalize_phone(request.form.get('phone'))
        password = request.form.get('password') or ''

        user = people.query.filter_by(phone=phone).first()
        if not user or not user.check_password(password):
            flash('Неверный номер телефона или пароль', 'error')
            return render_template('auth/login.html',
                                   phone=request.form.get('phone'))

        login_user(user)
        return redirect(request.args.get('next') or url_for('portal.dashboard'))

    return render_template('auth/login.html')


@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('portal.dashboard'))

    if request.method == 'POST':
        surname = (request.form.get('surname') or '').strip()
        name = (request.form.get('name') or '').strip()
        lastname = (request.form.get('lastname') or '').strip()
        apartment = (request.form.get('apartment') or '').strip()
        phone_raw = request.form.get('phone') or ''
        phone = _normalize_phone(phone_raw)
        password = request.form.get('password') or ''
        password2 = request.form.get('password2') or ''

        if not (surname and name):
            flash('Укажите фамилию и имя', 'error')
        elif not _PHONE_RE.match(phone_raw.strip()):
            flash('Введите корректный номер телефона', 'error')
        elif len(password) < 6:
            flash('Пароль должен быть не короче 6 символов', 'error')
        elif password != password2:
            flash('Пароли не совпадают', 'error')
        elif people.query.filter_by(phone=phone).first():
            flash('Аккаунт с таким номером уже существует', 'error')
        else:
            user = people(
                surname=surname,
                name=name,
                lastname=lastname or None,
                apartment=apartment or None,
                phone=phone,
                campus='khodynka',
                total_score=0,
            )
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash('Добро пожаловать в MYKHODYNKA!', 'success')
            return redirect(url_for('portal.dashboard'))

        return render_template('auth/register.html',
                               surname=surname, name=name, lastname=lastname,
                               apartment=apartment, phone=phone_raw)

    return render_template('auth/register.html')


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
