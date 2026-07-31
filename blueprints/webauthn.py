import base64
import json

from flask import Blueprint, request, session, jsonify
from flask_login import current_user, login_required, login_user

from db_settings import db, WebAuthnCredential, people
from fido2.server import Fido2Server
from fido2.webauthn import (
    PublicKeyCredentialRpEntity,
    PublicKeyCredentialUserEntity,
    UserVerificationRequirement,
    ResidentKeyRequirement,
    AttestedCredentialData,
)
from config import RP_ID, RP_NAME

webauthn_bp = Blueprint('webauthn', __name__)

rp = PublicKeyCredentialRpEntity(name=RP_NAME, id=RP_ID)
server = Fido2Server(rp)
WEBAUTHN_USER_VERIFICATION = UserVerificationRequirement.REQUIRED


def _json_serialize(obj):
    """Сериализует опции WebAuthn (в т.ч. enum'ы) в JSON для браузера."""
    return json.dumps(dict(obj.public_key) if hasattr(obj, 'public_key') else obj,
                      default=lambda o: getattr(o, 'value', str(o)))


def _b64enc(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()


def _b64dec(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + '=' * (-len(data) % 4))


@webauthn_bp.route('/biometric/register/begin', methods=['POST'])
@login_required
def biometric_register_begin():
    user = current_user
    user_handle = _b64dec(str(user.id))
    cred_entity = PublicKeyCredentialUserEntity(
        id=user_handle,
        name=user.phone or user.name,
        display_name=f'{user.name} {user.surname}',
    )

    existing = WebAuthnCredential.query.filter_by(user_id=user.id).all()
    allow = []
    for c in existing:
        allow.append(AttestedCredentialData.from_ctap1(
            _b64dec(c.credential_id), _b64dec(c.public_key)))

    request_options, state = server.register_begin(
        cred_entity,
        credentials=allow,
        user_verification=WEBAUTHN_USER_VERIFICATION,
        resident_key_requirement=ResidentKeyRequirement.DISCOURAGED,
    )
    session['webauthn_state'] = state
    return jsonify(json.loads(_json_serialize(request_options)))


@webauthn_bp.route('/biometric/register/complete', methods=['POST'])
@login_required
def biometric_register_complete():
    state = session.get('webauthn_state')
    if not state:
        return jsonify({'error': 'Сессия регистрации истекла, попробуйте снова'}), 400
    try:
        data = request.get_json(force=True)
        auth_data = server.register_complete(state, data)
    except Exception as exc:  # noqa: BLE001
        return jsonify({'error': f'Не удалось подтвердить устройство: {exc}'}), 400

    session.pop('webauthn_state', None)
    cred = auth_data.credential_data
    if cred is None:
        return jsonify({'error': 'Нет данных устройства'}), 400

    transports = json.dumps(request.get_json(force=True).get('transports') or [])

    new_cred = WebAuthnCredential(
        user_id=current_user.id,
        credential_id=_b64enc(cred.credential_id),
        public_key=_b64enc(cred.public_key.public_bytes),
        transports=transports,
        label='Face ID / Touch ID',
        sign_count=auth_data.sign_count,
    )
    db.session.add(new_cred)
    db.session.commit()
    return jsonify({'ok': True, 'message': 'Биометрический вход включён'})


@webauthn_bp.route('/biometric/login/begin', methods=['POST'])
def biometric_login_begin():
    """Начинает аутентификацию по сохранённому устройству."""
    data = request.get_json(force=True) or {}
    credential_id = (data.get('credential_id') or '').strip()

    if not credential_id:
        return jsonify({'error': 'Сначала включите вход по биометрии'}), 400

    stored = WebAuthnCredential.query.filter_by(credential_id=credential_id).first()
    if not stored:
        return jsonify({'error': 'Устройство не найдено'}), 404

    allow = [AttestedCredentialData.from_ctap1(
        _b64dec(stored.credential_id), _b64dec(stored.public_key))]
    request_options, state = server.authenticate_begin(
        credentials=allow, user_verification=WEBAUTHN_USER_VERIFICATION)
    session['webauthn_auth_state'] = state
    return jsonify(json.loads(_json_serialize(request_options)))


@webauthn_bp.route('/biometric/login/complete', methods=['POST'])
def biometric_login_complete():
    state = session.get('webauthn_auth_state')
    if not state:
        return jsonify({'error': 'Сессия истекла, попробуйте ещё раз'}), 400
    try:
        data = request.get_json(force=True)
        credential_id = _b64dec(data.get('id') or '')
        stored = WebAuthnCredential.query.filter_by(
            credential_id=_b64enc(credential_id)).first()
        if not stored:
            return jsonify({'error': 'Устройство не распознано'}), 404

        allow = [AttestedCredentialData.from_ctap1(
            _b64dec(stored.credential_id), _b64dec(stored.public_key))]
        auth_data = server.authenticate_complete(state, allow, data)
    except Exception as exc:  # noqa: BLE001
        return jsonify({'error': f'Ошибка проверки: {exc}'}), 400

    stored.sign_count = auth_data.sign_count
    user = db.session.get(people, stored.user_id)
    db.session.commit()
    session.pop('webauthn_auth_state', None)

    if not user:
        return jsonify({'error': 'Пользователь не найден'}), 404
    login_user(user)
    return jsonify({'ok': True, 'redirect': '/', 'user': user.name})


@webauthn_bp.route('/biometric/list', methods=['GET'])
@login_required
def biometric_list():
    creds = WebAuthnCredential.query.filter_by(user_id=current_user.id).all()
    return jsonify([{
        'id': str(c.id),
        'label': c.label or 'Устройство',
        'credential_id': c.credential_id,
        'created': c.created_at.strftime('%d.%m.%Y'),
    } for c in creds])


@webauthn_bp.route('/biometric/delete', methods=['POST'])
@login_required
def biometric_delete():
    data = request.get_json(force=True) or {}
    cid = (data.get('id') or '').strip()
    cred = WebAuthnCredential.query.filter_by(
        id=cid, user_id=current_user.id).first()
    if not cred:
        return jsonify({'error': 'Не найдено'}), 404
    db.session.delete(cred)
    db.session.commit()
    return jsonify({'ok': True})
