from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import current_user

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

# Демо-хранилище заявок (в памяти процесса)
_requests = [
    {"number": 1042, "category": "breakage", "title": "Что-то сломалось",
     "description": "Не работает домофон у 3 подъезда", "apartment": "58",
     "entrance": "3", "urgency": "high", "phone": "", "status": "in_progress", "created": "28.07"},
    {"number": 1039, "category": "cleaning", "title": "Уборка",
     "description": "Не вывезли мусор на площадке 5 этажа", "apartment": "58",
     "entrance": "3", "urgency": "normal", "phone": "", "status": "done", "created": "24.07"},
]
_next_number = [1043]


def _serialize(r):
    return dict(r, status_label=STATUS_LABELS.get(r["status"], r["status"]))


@portal.route('/')
def dashboard():
    name = current_user.name if current_user.is_authenticated else None
    return render_template('portal/apps.html', name=name)


@portal.route('/passes')
def passes():
    return render_template('portal/passes.html')


@portal.route('/passes/permanent')
def passes_permanent():
    return render_template('portal/passes_permanent.html')


@portal.route('/passes/temporary')
def passes_temporary():
    return render_template('portal/passes_temporary.html')


@portal.route('/passes/transport')
def passes_transport():
    return render_template('portal/passes_transport.html')


@portal.route('/passes/history')
def passes_history():
    return render_template('portal/passes_history.html')


@portal.route('/requests')
def requests_page():
    reqs = [_serialize(r) for r in reversed(_requests)]
    return render_template('portal/requests.html',
                           categories=REQUEST_CATEGORIES, requests=reqs)


@portal.route('/requests/new', methods=['POST'])
def requests_create():
    category = request.form.get('category', 'other')
    if category not in CATEGORY_TITLES:
        category = 'other'
    description = (request.form.get('description') or '').strip()

    if not description:
        flash('Опишите проблему, чтобы создать заявку', 'error')
        return redirect(url_for('portal.requests_page'))

    number = _next_number[0]
    _next_number[0] += 1
    _requests.append({
        "number": number,
        "category": category,
        "title": CATEGORY_TITLES[category],
        "description": description,
        "apartment": (request.form.get('apartment') or '').strip(),
        "entrance": (request.form.get('entrance') or '').strip(),
        "urgency": request.form.get('urgency', 'normal'),
        "phone": (request.form.get('phone') or '').strip(),
        "status": "new",
        "created": datetime.now().strftime('%d.%m'),
    })
    flash(f'Заявка №{number} создана — мы уже её получили', 'success')
    return redirect(url_for('portal.requests_page'))


@portal.route('/appeals')
def appeals():
    return render_template('portal/appeals.html')


@portal.route('/messages')
def messages():
    return render_template('portal/messages.html')
