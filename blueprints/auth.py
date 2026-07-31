from flask import Blueprint, render_template, request, redirect, url_for

auth = Blueprint('auth', __name__, template_folder='../templates/auth')


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        phone = request.form.get('phone')
        password = request.form.get('password')
        # TODO: validate credentials
        return redirect(url_for('portal.dashboard'))
    return render_template('auth/login.html')


@auth.route('/register', methods=['GET', 'POST'])
def register():
    return render_template('auth/register.html')
