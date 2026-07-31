from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import current_user, login_required

from db_settings import db, ServiceRequest, GuestPass, Notification, people

portal = Blueprint('portal', __name__, template_folder='../templates/portal')


# ───── Заявки в ЖК ─────

REQUEST_CATEGORIES = [
    {"id": "breakage",  "icon": "🔧", "title": "Что-то сломалось",     "desc": "Дверь, замок, домофон, лифт, освещение"},
    {"id": "master",    "icon": "🛠️", "title": "Нужен мастер",          "desc": "Сантехника, электрика, мелкий ремонт"},
    {"id": "cleaning",  "icon": "🧹", "title": "Уборка",                "desc": "Подъезд, территория, вывоз мусора"},
    {"id": "equipment", "icon": "🔦", "title": "Замена оборудования",   "desc": "Лампочки, батарейки, счётчики"},
    {"id": "meeting",   "icon": "👥", "title": "Собрание жителей",      "desc": "Инициировать встречу"},
    {"id": "other",     "icon": "💬", "title": "Другое",                "desc": "Любой другой вопрос"},
]

CATEGORY_TITLES = {c["id"]: c["title"] for c in REQUEST_CATEGORIES}
STATUS_LABELS = {"new": "Новая", "in_progress": "В работе", "done": "Выполнена"}

GUEST_CATEGORY_TITLES = {
    "guest": "Гость",
    "courier": "Курьер",
    "delivery": "Доставка",
    "transport": "Транспорт",
    "permanent": "Постоянный",
}

GUEST_STATUS_LABELS = {"new": "Ожидает", "approved": "Разрешён", "done": "Прошёл", "rejected": "Отклонён", "arrived": "Гость прибыл"}


def _next_pass_number():
    top = db.session.query(db.func.max(GuestPass.number)).scalar()
    return (top or 0) + 1


def _next_number():
    top = db.session.query(db.func.max(ServiceRequest.number)).scalar()
    return (top or 0) + 1


def _serialize(r):
    return {
        "number": r.number,
        "category": r.category,
        "title": r.title,
        "description": r.description,
        "apartment": r.apartment,
        "entrance": r.entrance,
        "urgency": r.urgency,
        "phone": r.phone,
        "status": r.status,
        "status_label": STATUS_LABELS.get(r.status, r.status),
        "created": r.created_at.strftime('%d.%m'),
    }


@portal.route('/')
@login_required
def dashboard():
    name = current_user.name if current_user.is_authenticated else None
    return render_template('portal/apps.html', name=name)


@portal.route('/passes')
@login_required
def passes():
    rows = (GuestPass.query
            .filter(GuestPass.user_id == current_user.id)
            .order_by(GuestPass.created_at.desc())
            .all())
    passes_ = [{
        "id": p.id,
        "number": p.number,
        "category": p.category,
        "category_label": GUEST_CATEGORY_TITLES.get(p.category, p.category),
        "transport": p.transport,
        "guest_name": p.guest_name,
        "guest_phone": p.guest_phone,
        "visit_at": p.visit_at.strftime('%d.%m %H:%M') if p.visit_at else None,
        "status": p.status,
        "status_label": GUEST_STATUS_LABELS.get(p.status, p.status),
        "created": p.created_at.strftime('%d.%m'),
    } for p in rows]
    return render_template('portal/passes.html', passes=passes_)


@portal.route('/passes/new', methods=['POST'])
@login_required
def passes_create():
    category = request.form.get('category', 'guest')
    if category not in GUEST_CATEGORY_TITLES:
        category = 'guest'
    guest_name = (request.form.get('guest_name') or '').strip()
    guest_phone = (request.form.get('guest_phone') or '').strip()
    transport = request.form.get('transport', 'walking')
    visit_at_raw = request.form.get('visit_at') or None

    if not guest_name:
        flash('Укажите имя гостя', 'error')
        return redirect(url_for('portal.passes'))

    from datetime import datetime
    visit_at = None
    if visit_at_raw:
        try:
            visit_at = datetime.fromisoformat(visit_at_raw)
        except ValueError:
            visit_at = None

    gp = GuestPass(
        user_id=current_user.id,
        number=_next_pass_number(),
        category=category,
        transport=transport,
        visit_at=visit_at,
        guest_name=guest_name,
        guest_phone=guest_phone or None,
        status="new",
    )
    db.session.add(gp)
    db.session.commit()
    flash(f'Пропуск №{gp.number} для гостя создан', 'success')
    return redirect(url_for('portal.passes'))


# ───── Публичная страница гостя (открывается по ссылке, без входа) ─────

@portal.route('/p/<uuid>')
def guest_pass(uuid):
    gp = GuestPass.query.get(uuid)
    if not gp:
        return render_template('portal/guest_pass.html', error=True), 404
    return render_template('portal/guest_pass.html', pass_info={
        "id": gp.id,
        "number": gp.number,
        "category_label": GUEST_CATEGORY_TITLES.get(gp.category, gp.category),
        "guest_name": gp.guest_name,
        "guest_phone": gp.guest_phone,
        "transport": gp.transport,
        "visit_at": gp.visit_at.strftime('%d.%m.%Y в %H:%M') if gp.visit_at else None,
        "status": gp.status,
        "status_label": GUEST_STATUS_LABELS.get(gp.status, gp.status),
    })


@portal.route('/p/<uuid>/arrived', methods=['POST'])
def guest_arrived(uuid):
    """Гость сообщает, что он у входа. Жителю уходит уведомление."""
    from datetime import datetime
    gp = GuestPass.query.get(uuid)
    if not gp:
        return jsonify({'error': 'Пропуск не найден'}), 404

    if gp.status == 'rejected':
        return jsonify({'error': 'Вход по этому пропуску запрещён'}), 403

    if gp.status != 'arrived':
        gp.status = 'arrived'
        gp.arrived_at = datetime.now()

        # Уведомляем жителя (один раз, при первом прибытии)
        resident = db.session.get(people, gp.user_id) if gp.user_id else None
        if resident:
            cat = GUEST_CATEGORY_TITLES.get(gp.category, 'гость')
            notif = Notification(
                user_id=resident.id,
                type='guest_arrived',
                title='Гость у входа',
                body=f'{gp.guest_name or "Гость"} прибыл ({cat}, пропуск №{gp.number}).',
                pass_id=gp.id,
            )
            db.session.add(notif)
        db.session.commit()

    return jsonify({'ok': True})


@portal.route('/notifications', methods=['GET'])
@login_required
def notifications():
    rows = (Notification.query
            .filter_by(user_id=current_user.id)
            .order_by(Notification.created_at.desc())
            .limit(50).all())
    items = [{
        "id": str(n.id),
        "type": n.type,
        "title": n.title,
        "body": n.body,
        "is_read": n.is_read,
        "created": n.created_at.strftime('%d.%m %H:%M'),
    } for n in rows]
    return render_template('portal/messages.html', notifications=items)


@portal.route('/notifications/read', methods=['POST'])
@login_required
def notifications_read():
    db.session.query(Notification).filter_by(
        user_id=current_user.id, is_read=False).update({'is_read': True})
    db.session.commit()
    return jsonify({'ok': True})


@portal.route('/passes/permanent')
@login_required
def passes_permanent():
    return render_template('portal/passes_permanent.html')


@portal.route('/passes/temporary')
@login_required
def passes_temporary():
    return render_template('portal/passes_temporary.html')


@portal.route('/passes/transport')
@login_required
def passes_transport():
    return render_template('portal/passes_transport.html')


@portal.route('/passes/history')
@login_required
def passes_history():
    return render_template('portal/passes_history.html')


@portal.route('/requests')
@login_required
def requests_page():
    rows = (ServiceRequest.query
            .filter(ServiceRequest.user_id == current_user.id)
            .order_by(ServiceRequest.created_at.desc())
            .all())
    reqs = [_serialize(r) for r in rows]
    return render_template('portal/requests.html',
                           categories=REQUEST_CATEGORIES, requests=reqs)


@portal.route('/requests/new', methods=['POST'])
@login_required
def requests_create():
    category = request.form.get('category', 'other')
    if category not in CATEGORY_TITLES:
        category = 'other'
    description = (request.form.get('description') or '').strip()

    if not description:
        flash('Опишите проблему, чтобы создать заявку', 'error')
        return redirect(url_for('portal.requests_page'))

    req = ServiceRequest(
        user_id=current_user.id,
        number=_next_number(),
        category=category,
        title=CATEGORY_TITLES[category],
        description=description,
        apartment=(request.form.get('apartment') or '').strip() or None,
        entrance=(request.form.get('entrance') or '').strip() or None,
        urgency=request.form.get('urgency', 'normal'),
        phone=(request.form.get('phone') or '').strip() or None,
        status="new",
    )
    db.session.add(req)
    db.session.commit()
    flash(f'Заявка №{req.number} создана — мы уже её получили', 'success')
    return redirect(url_for('portal.requests_page'))


@portal.route('/appeals')
@login_required
def appeals():
    return render_template('portal/appeals.html')


@portal.route('/messages')
@login_required
def messages():
    return render_template('portal/messages.html')


@portal.route('/account')
@login_required
def account():
    u = current_user
    full_name = ' '.join(x for x in (u.surname, u.name, u.lastname) if x)
    phone = u.phone or ''
    if len(phone) == 11 and phone.startswith('7'):
        phone = '+7 ' + phone[1:4] + ' ' + phone[4:7] + '-' + phone[7:9] + '-' + phone[9:11]
    return render_template('portal/account.html',
                           full_name=full_name, phone=phone,
                           apartment=u.apartment)


# ───── Счётчики ─────

@portal.route('/meters')
@login_required
def meters():
    return render_template('portal/service_page.html', title='Счётчики',
                           subtitle='Показания воды, света и тепла', icon='🧮',
                           intro='Передавайте показания счётчиков и следите за расходами.',
                           items=[
                               {"icon": "💧", "title": "Передать показания", "desc": "Вода: холодная и горячая"},
                               {"icon": "💡", "title": "Электроэнергия", "desc": "Передать и посмотреть историю"},
                               {"icon": "🔥", "title": "Тепло и отопление", "desc": "Показания тепловых счётчиков"},
                               {"icon": "📊", "title": "История начислений", "desc": "Динамика по месяцам"},
                           ])


# ───── Парковка ─────

@portal.route('/parking')
@login_required
def parking():
    return render_template('portal/service_page.html', title='Парковка',
                           subtitle='Места, абонементы, гостевой доступ', icon='🅿️',
                           intro='Управление парковочными местами и абонементами.',
                           items=[
                               {"icon": "🅿️", "title": "Мои места", "desc": "Список парковочных мест"},
                               {"icon": "🎟️", "title": "Абонемент", "desc": "Продлить или оформить"},
                               {"icon": "🚗", "title": "Гостевой въезд", "desc": "Разовый доступ для гостя"},
                               {"icon": "🕘", "title": "История въездов", "desc": "Кто и когда заезжал"},
                           ])


# ───── Консьерж ─────

@portal.route('/concierge')
@login_required
def concierge():
    return render_template('portal/service_page.html', title='Консьерж',
                           subtitle='Услуги на стойке дома', icon='🛎️',
                           intro='Закажите услуги, не спускаясь на первый этаж.',
                           items=[
                               {"icon": "🔑", "title": "Ключи и доступ", "desc": "Дубликаты, пропуска, брелоки"},
                               {"icon": "📦", "title": "Принять посылку", "desc": "Хранение доставки у консьержа"},
                               {"icon": "🧾", "title": "Документы УК", "desc": "Получить справку или выписку"},
                               {"icon": "❓", "title": "Вопрос консьержу", "desc": "Связаться со стойкой дома"},
                           ])


# ───── Коворкинг ─────

@portal.route('/coworking')
@login_required
def coworking():
    return render_template('portal/service_page.html', title='Коворкинг',
                           subtitle='Переговорки и рабочие места', icon='💼',
                           intro='Бронируйте переговорные комнаты и рабочие места в доме.',
                           items=[
                               {"icon": "🪑", "title": "Рабочее место", "desc": "Бронь места на день"},
                               {"icon": "💬", "title": "Переговорная", "desc": "Комната для встреч"},
                               {"icon": "🎤", "title": "Лофт/события", "desc": "Площадка для мероприятий"},
                               {"icon": "🕘", "title": "Мои брони", "desc": "Текущие и прошедшие бронирования"},
                           ])
