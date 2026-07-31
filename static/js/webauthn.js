/* ── WebAuthn: вход по Face ID / Touch ID ── */

function webauthnAvailable() {
    return window.PublicKeyCredential && window.isSecureContext;
}

async function webauthnCall(url, body) {
    const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: body ? JSON.stringify(body) : undefined,
    });
    return res.json();
}

async function webauthnLogin() {
    const btn = document.getElementById('biometricBtn');
    if (!btn) return;
    if (!webauthnAvailable()) {
        alert('Биометрия доступна только в защищённом контексте (https или localhost).');
        return;
    }

    const id = btn.dataset.credentialId;
    if (!id) {
        alert('Сначала включите вход по биометрии в разделе «Аккаунт».');
        return;
    }

    btn.disabled = true;
    const original = btn.innerHTML;
    btn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Проверяем…';

    try {
        const options = await webauthnCall('/biometric/login/begin', { credential_id: id });
        if (options.error) throw new Error(options.error);
        const credential = await navigator.credentials.get({ publicKey: options });

        const result = await webauthnCall('/biometric/login/complete', credential);
        if (result.error) throw new Error(result.error);
        window.location.href = result.redirect || '/';
    } catch (err) {
        alert('Биометрический вход не удался: ' + err.message);
        btn.disabled = false;
        btn.innerHTML = original;
    }
}

document.addEventListener('DOMContentLoaded', function () {
    const btn = document.getElementById('biometricBtn');
    if (btn) {
        // Показываем кнопку только если есть сохранённый ключ и есть WebAuthn
        const id = btn.dataset.credentialId;
        if (id && webauthnAvailable()) {
            btn.hidden = false;
            btn.addEventListener('click', webauthnLogin);
        }
    }
});

/* ── Аккаунт: включение/список/удаление биометрии ── */
async function webauthnEnroll() {
    if (!webauthnAvailable()) {
        alert('Биометрия доступна только в защищённом контексте (https или localhost).');
        return;
    }
    const btn = document.getElementById('biometricEnrollBtn');
    if (btn) { btn.disabled = true; }

    try {
        const options = await webauthnCall('/biometric/register/begin');
        if (options.error) throw new Error(options.error);

        // Преобразуем строки в ArrayBuffer для navigator.credentials.create
        options.challenge = base64ToBuffer(options.challenge);
        options.user.id = base64ToBuffer(options.user.id);
        if (options.excludeCredentials) {
            options.excludeCredentials.forEach(function (c) { c.id = base64ToBuffer(c.id); });
        }

        const credential = await navigator.credentials.create({ publicKey: options });
        const result = await webauthnCall('/biometric/register/complete', credential);
        if (result.error) throw new Error(result.error);
        alert(result.message || 'Биометрический вход включён!');
        webauthnRefreshList();
    } catch (err) {
        alert('Не удалось настроить биометрию: ' + err.message);
    } finally {
        if (btn) { btn.disabled = false; }
    }
}

function base64ToBuffer(b64) {
    const bin = atob(b64);
    const bytes = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    return bytes.buffer;
}

async function webauthnDelete(id, btn) {
    if (!confirm('Отключить биометрический вход для этого устройства?')) return;
    await webauthnCall('/biometric/delete', { id: id });
    webauthnRefreshList();
}

async function webauthnRefreshList() {
    const wrap = document.getElementById('biometricList');
    if (!wrap) return;
    try {
        const res = await fetch('/biometric/list', { headers: { 'Accept': 'application/json' } });
        const creds = await res.json();
        if (!Array.isArray(creds) || creds.length === 0) {
            wrap.innerHTML = '<p class="hint">Устройства не добавлены. Включите вход по Face ID / Touch ID.</p>';
            return;
        }
        wrap.innerHTML = creds.map(function (c) {
            return '<div class="biometric-row">' +
                '<div class="biometric-info">' +
                '<i class="fa-solid fa-fingerprint"></i>' +
                '<div><div class="biometric-name">' + (c.label || 'Устройство') + '</div>' +
                '<div class="hint">добавлено ' + c.created + '</div></div></div>' +
                '<button type="button" class="biometric-del" onclick="webauthnDelete(\'' + c.id + '\', this)">' +
                '<i class="fa-solid fa-trash-can"></i></button></div>';
        }).join('');
    } catch (e) { /* ignore */ }
}

document.addEventListener('DOMContentLoaded', function () {
    const enrollBtn = document.getElementById('biometricEnrollBtn');
    if (enrollBtn) {
        enrollBtn.addEventListener('click', webauthnEnroll);
        webauthnRefreshList();
    }
});
