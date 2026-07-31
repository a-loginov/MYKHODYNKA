from functools import wraps
from datetime import datetime

from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, session)

from db_settings import db, GuestPass, Contractor, ProblemReport, people, Notification
from config import SECURITY_PASSWORD

security = Blueprint('security', __name__, url_prefix='/security',
                     template_folder='../templates/security')


GUEST_CATEGORY_TITLES = {
    "guest": "Гость", "courier": "Курьер", "delivery": "Доставка",
    "transport": "Транспорт", "permanent": "Постоянный",
}
GUEST_STATUS_LABELS = {"new": "Ожидает", "approved": "Разрешён", "done": "Прошёл",
                       "rejected": "Отклонён", "arrived": "Гость у входа"}
TRANSPORT_LABELS = {"walking": "Пешком", "car": "Авто", "taxi": "Такси", "cargo": "Грузовой"}


# ───── Защита паролем ─────

def guard_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not session.get('is_guard'):
            return redirect(url_for('security.login', next=request.path))
        return view(*args, **kwargs)
    return wrapper


@security.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('is_guard'):
        return redirect(url_for('security.dashboard'))
    if request.method == 'POST':
        password = request.form.get('password') or ''
        if password and password == SECURITY_PASSWORD:
            session['is_guard'] = True
            return redirect(request.args.get('next') or url_for('security.dashboard'))
        flash('Неверный пароль', 'error')
    return render_template('security/login.html')


@security.route('/logout')
def logout():
    session.pop('is_guard', None)
    return redirect(url_for('security.login'))


# ───── Панель охраны ─────

@security.route('/')
@guard_required
def dashboard():
    rows = (GuestPass.query
            .filter(GuestPass.status.in_(['new', 'approved', 'arrived']))
            .order_by(GuestPass.created_at.desc()).all())
    passes = [{
        "id": str(p.id), "number": p.number,
        "guest_name": p.guest_name or 'Без имени',
        "guest_phone": p.guest_phone,
        "category_label": GUEST_CATEGORY_TITLES.get(p.category, p.category),
        "transport_label": TRANSPORT_LABELS.get(p.transport, p.transport or '—'),
        "visit_at": p.visit_at.strftime('%d.%m %H:%M') if p.visit_at else None,
        "status": p.status,
        "status_label": GUEST_STATUS_LABELS.get(p.status, p.status),
        "resident": _resident_name(p.user_id),
    } for p in rows]

    contractors = (Contractor.query
                   .filter_by(status='active')
                   .order_by(Contractor.created_at.desc()).all())
    contractors_view = [{
        "id": str(c.id), "name": c.name, "company": c.company,
        "phone": c.phone, "purpose": c.purpose,
        "created": c.created_at.strftime('%d.%m %H:%M'),
    } for c in contractors]

    return render_template('security/dashboard.html',
                           passes=passes, contractors=contractors_view)


def _resident_name(user_id):
    if not user_id:
        return None
    u = db.session.get(people, user_id)
    if not u:
        return None
    parts = [x for x in (u.surname, u.name) if x]
    label = ' '.join(parts)
    if u.apartment:
        label += f' · кв. {u.apartment}'
    return label or None


@security.route('/pass/<uuid>/<action>', methods=['POST'])
@guard_required
def pass_action(uuid, action):
    gp = GuestPass.query.get(uuid)
    if not gp:
        flash('Пропуск не найден', 'error')
        return redirect(url_for('security.dashboard'))

    if action == 'admit':          # впустить — гость прошёл
        gp.status = 'done'
        flash(f'Пропуск №{gp.number}: гость впущен', 'success')
    elif action == 'close':        # закрыть — повторно не пройдёт
        gp.status = 'rejected'
        flash(f'Пропуск №{gp.number} закрыт', 'success')
    else:
        flash('Неизвестное действие', 'error')
        return redirect(url_for('security.dashboard'))

    # Уведомим жителя об итоге прохода
    if gp.user_id:
        resident = db.session.get(people, gp.user_id)
        if resident:
            done = action == 'admit'
            db.session.add(Notification(
                user_id=resident.id,
                type='guest_arrived',
                title='Гость впущен' if done else 'Пропуск закрыт',
                body=(f'{gp.guest_name or "Гость"} прошёл (пропуск №{gp.number}).'
                      if done else
                      f'Охрана закрыла пропуск №{gp.number}.'),
                pass_id=gp.id,
            ))
    db.session.commit()
    return redirect(url_for('security.dashboard'))


# ───── Подрядчики ─────

@security.route('/contractors', methods=['POST'])
@guard_required
def contractor_add():
    name = (request.form.get('name') or '').strip()
    if not name:
        flash('Укажите имя подрядчика', 'error')
        return redirect(url_for('security.dashboard'))
    db.session.add(Contractor(
        name=name,
        company=(request.form.get('company') or '').strip() or None,
        phone=(request.form.get('phone') or '').strip() or None,
        purpose=(request.form.get('purpose') or '').strip() or None,
        status='active',
    ))
    db.session.commit()
    flash('Подрядчик зарегистрирован', 'success')
    return redirect(url_for('security.dashboard'))


@security.route('/contractors/<uuid>/close', methods=['POST'])
@guard_required
def contractor_close(uuid):
    c = Contractor.query.get(uuid)
    if c:
        c.status = 'closed'
        c.closed_at = datetime.now()
        db.session.commit()
        flash('Подрядчик отмечен ушедшим', 'success')
    return redirect(url_for('security.dashboard'))


# ───── Сообщить о проблеме (→ админу) ─────

@security.route('/report', methods=['POST'])
@guard_required
def report_problem():
    message = (request.form.get('message') or '').strip()
    if not message:
        flash('Опишите проблему', 'error')
        return redirect(url_for('security.dashboard'))
    db.session.add(ProblemReport(
        source='security', author='Охрана', message=message, status='new'))
    db.session.commit()
    flash('Сообщение отправлено администратору', 'success')
    return redirect(url_for('security.dashboard'))
