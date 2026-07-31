from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import current_user, login_required

from db_settings import db, ServiceRequest

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
    return render_template('portal/passes.html')


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
