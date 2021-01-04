#!/usr/bin/python3

import os
import secrets
import psycopg2
import psycopg2.extras
from flask import Flask, request, url_for, render_template, flash, redirect, abort, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from middleware.email_controler import mail_sender
from smtplib import SMTPRecipientsRefused
from datetime import timedelta

from config.config import config, is_safe_url

app = Flask(__name__.split('.')[0])

login_manager = LoginManager()
login_manager.init_app(app)

app.config['SECRET_KEY'] = os.urandom(24)
app.config.from_pyfile('config/config.cfg')
app.config['USE_SESSION_FOR_NEXT'] = True
app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=14)


class User(UserMixin):
    def __init__(self, email, username, parent, inheritor, referral):
        self.id = email
        self.name = username
        self.parent = parent
        self.inheritor = inheritor
        self.referral = referral


@login_manager.user_loader
def load_user(email):
    conn = None
    cur = None

    try:
        params = config()
        conn = psycopg2.connect(**params)
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cur.execute('SELECT username, referral_key, parent_status, inheritor_status '
                    'FROM chk_email_return_username_pswd_referral_parent_inheritor(%s)',
                    (email,))
        result = cur.fetchone()
        if result['username']:
            username = result['username']
            referral = result['referral_key']
            parent = result['parent_status']
            inheritor = result['inheritor_status']
            if inheritor == 0:
                inheritor = 'Я регистрирован без реферального кода'
            elif inheritor == 1:
                inheritor = 'Я регистрирован по реферальному программе.'
            user = User(email, username, parent, inheritor, referral)
            return user
        else:
            return None

    except (Exception, psycopg2.DatabaseError):
        abort(500)

    finally:
        if cur is not None:
            cur.close()
        if conn is not None:
            conn.close()


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')


@app.route('/register/', methods=['GET', 'POST'])
def register():
    '''Collect data from form.
    SQL check ip paused 2 min after registration.
    SQL check email status and write registering user in db
    with status 0 or answers about wrong email type.
    If true referral code was given it consolidate
    pather and inheritor users then wrote in db with status 0.
    f'''
    if not current_user.is_authenticated:
        if request.method == 'POST':
            conn = None
            cur = None

            try:
                params = config()
                conn = psycopg2.connect(**params)
                cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

                username = request.form['username'].strip()
                pswd = generate_password_hash(request.form['password'], method='sha256')
                email = request.form['email'].strip()
                repair = secrets.token_urlsafe(12)
                referral = secrets.token_urlsafe(10)
                ip_address = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)

                sql_insert_data = (username, pswd, email, repair, referral, ip_address)
                cur.execute('SELECT chk_new_user_for_duplication_and_ip_attack_then_add(%s, %s, %s, %s, %s, %s)',
                            sql_insert_data)
                chk_answer = cur.fetchone()[0]

                if chk_answer == 'registration':
                    url = 'http://localhost:5000' + url_for('reg_success', url=repair)
                    try:
                        mail_sender(email, url, app)
                        conn.commit()
                        parent = request.form['referral'].strip()
                        if parent and len(parent) == 14:
                            cur.execute('SELECT insert_into_referral_parent_inheritor_id(%s, %s)', (parent, email))
                            conn.commit()

                    except SMTPRecipientsRefused:
                        flash('Ошибка отправки сообщения, проверьте адресс почты.')
                        return redirect(url_for('message'))

                    flash('Войдите на почту, чтобы закончить регистрацию')
                    return redirect(url_for('message'))

                elif chk_answer == 'registered':
                    flash('Почта уже зарегестрированна, авторизуйтесь или востановите аккаунт.')
                    return redirect(url_for('logi'))

                elif chk_answer == 'check email':
                    flash('На вашу почту уже было отправлено письмо с подтвеждением регистрации')
                    return redirect(url_for('message'))

                elif chk_answer == 'ip_attack':
                    flash('Ошибка: Вы недавно регистрировались с этого ip адресса')
                    return redirect(url_for('message'))

                elif chk_answer == 'unknown':
                    flash('Низвестная ошибка базы данных.')
                    return redirect(url_for('message'))

                flash('Низвестная ошибка функции БД "chk_new_user_for_duplication_and_ip_attack_then_add"')
                return redirect(url_for('message'))

            except (Exception, psycopg2.DatabaseError) as error:
                flash('Error: ', error)
                return redirect(url_for('message'))

            finally:
                if cur is not None:
                    cur.close()
                if conn is not None:
                    conn.close()
        return render_template('register.html')
    abort(404)


@app.route('/register/complete/<string:url>')
def reg_success(url):
    '''Checks url
    SQL Change register-repair url for new one
    and change status 1 - registered or return
    another email status answers.
    '''
    if len(url) == 16:
        conn = None
        cur = None

        try:
            params = config()
            conn = psycopg2.connect(**params)
            cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

            repair = secrets.token_urlsafe(12)
            cur.execute('SELECT chk_url_change_reg_status(%s, %s)', (url, repair))
            chk_answer = cur.fetchone()[0]

            if chk_answer == 'updated':
                conn.commit()
                flash('Вы успешно зарегистрированы, пожалуйста авторизуйтесь')
                return redirect(url_for('login'))

            elif chk_answer == 'registered':
                flash('Ваша почта уже зарегестрированна')
                return redirect(url_for('login'))

            elif chk_answer == 'unknown':
                flash('Не существующая ссылка на регистрацию')
                return redirect(url_for('register'))

        except (Exception, psycopg2.DatabaseError) as error:
            flash('Error: ', error)
            return redirect(url_for('message'))

        finally:
            if cur is not None:
                cur.close()
            if conn is not None:
                conn.close()
    abort(404)

@app.route('/login', methods=['GET', 'POST'])
def login():
    ''''''
    if not current_user.is_authenticated:
        if request.method == 'POST':
            conn = None
            cur = None
            try:
                params = config()
                conn = psycopg2.connect(**params)
                cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

                email = request.form['email']
                auth_pswd = request.form['password']

                cur.execute('SELECT username, pswd, referral_key, parent_status, inheritor_status '
                            'FROM chk_email_return_username_pswd_referral_parent_inheritor(%s)',
                            (email,))
                result = cur.fetchone()
                if result['username']:
                    db_pswd = result['pswd']
                    if check_password_hash(db_pswd, auth_pswd):
                        username = result['username']
                        referral = result['referral_key']
                        parent = result['parent_status']
                        inheritor = result['inheritor_status']
                        login_user(User(email, username, parent, inheritor, referral), remember=True)
                        return redirect(url_for('index'))

                    flash('Неправильный логин или пароль')
                    return redirect(url_for('login'))

                flash('Неправильный логин или пароль')
                return redirect(url_for('login'))

            except (Exception, psycopg2.DatabaseError) as error:
                flash('Error: ', error)
                return redirect(url_for('message'))

            finally:
                if cur is not None:
                    cur.close()
                if conn is not None:
                    conn.close()
        return render_template('login.html')
    abort(404)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/register/message')
def message():
    return render_template('end_reg.html')


if __name__ == '__main__':
    # app.run(debug=True)
    from waitress import serve
    serve(app, host="127.0.0.1", port=5000)
