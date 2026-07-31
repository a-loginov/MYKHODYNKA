import os
import sys
import signal
from functools import wraps
from datetime import datetime

from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, session, jsonify)
from sqlalchemy import text

from db_settings import (db, people, ServiceRequest, GuestPass,
                         ProblemReport, Contractor)
from config import MASTER_PASSWORD

admin = Blueprint('admin', __name__, url_prefix='/admin',
                  template_folder='../templates/admin')


# ───── Защита паролем ─────

def admin_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not session.get('is_admin'):
            return redirect(url_for('admin.login', next=request.path))
        return view(*args, **kwargs)
    return wrapper


@admin.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('is_admin'):
        return redirect(url_for('admin.dashboard'))
    if request.method == 'POST':
        password = request.form.get('password') or ''
        if password and password == MASTER_PASSWORD:
            session['is_admin'] = True
            return redirect(request.args.get('next') or url_for('admin.dashboard'))
        flash('Неверный пароль', 'error')
    return render_template('admin/login.html')


@admin.route('/logout')
def logout():
    session.pop('is_admin', None)
    return redirect(url_for('admin.login'))


# ───── Панель ─────

STATUS_LABELS = {"new": "Новая", "in_progress": "В работе", "done": "Выполнена"}
GUEST_STATUS_LABELS = {"new": "Ожидает", "approved": "Разрешён", "done": "Прошёл",
                       "rejected": "Отклонён", "arrived": "Гость прибыл"}


@admin.route('/')
@admin_required
def dashboard():
    stats = {
        "residents": people.query.count(),
        "passes": GuestPass.query.count(),
        "passes_active": GuestPass.query.filter(
            GuestPass.status.in_(['new', 'approved', 'arrived'])).count(),
        "requests": ServiceRequest.query.count(),
        "requests_new": ServiceRequest.query.filter_by(status='new').count(),
        "problems_new": ProblemReport.query.filter_by(status='new').count(),
    }

    requests_ = (ServiceRequest.query
                 .order_by(ServiceRequest.created_at.desc()).limit(15).all())
    requests_view = [{
        "id": str(r.id), "number": r.number, "title": r.title,
        "category": r.category, "apartment": r.apartment,
        "status": r.status, "status_label": STATUS_LABELS.get(r.status, r.status),
        "created": r.created_at.strftime('%d.%m %H:%M'),
    } for r in requests_]

    passes_ = (GuestPass.query
               .order_by(GuestPass.created_at.desc()).limit(15).all())
    passes_view = [{
        "number": p.number, "guest_name": p.guest_name, "category": p.category,
        "status": p.status, "status_label": GUEST_STATUS_LABELS.get(p.status, p.status),
        "created": p.created_at.strftime('%d.%m %H:%M'),
    } for p in passes_]

    problems = (ProblemReport.query
                .order_by(ProblemReport.status.desc(), ProblemReport.created_at.desc())
                .limit(30).all())
    problems_view = [{
        "id": str(pr.id), "source": pr.source, "author": pr.author,
        "message": pr.message, "status": pr.status,
        "created": pr.created_at.strftime('%d.%m %H:%M'),
    } for pr in problems]

    return render_template('admin/dashboard.html', stats=stats,
                           requests=requests_view, passes=passes_view,
                           problems=problems_view, health=_health())


def _health():
    """Быстрая проверка соединения с БД."""
    try:
        db.session.execute(text('SELECT 1'))
        return {"db": True}
    except Exception:  # noqa: BLE001
        db.session.rollback()
        return {"db": False}


@admin.route('/health')
@admin_required
def health():
    return jsonify(_health())


# ───── Действия ─────

@admin.route('/requests/<uuid>/resolve', methods=['POST'])
@admin_required
def resolve_request(uuid):
    req = ServiceRequest.query.get(uuid)
    if req:
        req.status = 'done'
        db.session.commit()
        flash(f'Заявка №{req.number} отмечена выполненной', 'success')
    return redirect(url_for('admin.dashboard'))


@admin.route('/problems/<uuid>/resolve', methods=['POST'])
@admin_required
def resolve_problem(uuid):
    pr = ProblemReport.query.get(uuid)
    if pr:
        pr.status = 'resolved'
        pr.resolved_at = datetime.now()
        db.session.commit()
        flash('Проблема отмечена решённой', 'success')
    return redirect(url_for('admin.dashboard'))


@admin.route('/restart', methods=['POST'])
@admin_required
def restart():
    """Мягкая перезагрузка: сигнал gunicorn на graceful-reload воркеров.

    В gunicorn мастер-процесс по SIGHUP плавно перезапускает воркеры без
    простоя. В dev-режиме (flask/app.run) сигнал не отправляем, чтобы не
    убить оболочку — просто сообщаем, что действие доступно только в проде.
    """
    if 'gunicorn' in sys.modules:
        try:
            os.kill(os.getppid(), signal.SIGHUP)
            return jsonify({'ok': True,
                            'message': 'Отправлен сигнал перезагрузки — воркеры обновляются.'})
        except Exception as exc:  # noqa: BLE001
            return jsonify({'ok': False, 'message': f'Не удалось: {exc}'}), 500
    return jsonify({'ok': False,
                    'message': 'Мягкая перезагрузка доступна только в рабочем окружении (gunicorn).'}), 400
