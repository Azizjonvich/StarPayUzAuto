// StarPayUz - Common JavaScript Functions

const STARS_MIN = 50;
const STARS_MAX = 1000000;

const tg = window.Telegram.WebApp;
tg.expand();
tg.ready();
tg.setHeaderColor('#030712');
tg.setBackgroundColor('#030712');

let userBalance = 0;

// API base — can be overridden per-page via window.API_BASE
// e.g. in stars.html: <script>window.API_BASE = 'https://your-railway-url.railway.app';</script>
function getApiBase() {
    return (typeof window.API_BASE !== 'undefined' && window.API_BASE)
        ? window.API_BASE.replace(/\/$/, '')
        : '';
}

document.addEventListener('DOMContentLoaded', function () {
    fillUsernameFromTelegram();
    loadUserBalance();
});

function fillUsernameFromTelegram() {
    const input = document.getElementById('username');
    const user = tg.initDataUnsafe?.user;
    if (input && user?.username && !input.value.trim()) {
        input.value = '@' + user.username;
    }
}

function loadUserBalance() {
    const balanceElement = document.getElementById('balance');
    if (!balanceElement) return;

    const userId = tg.initDataUnsafe?.user?.id;
    if (!userId) {
        balanceElement.textContent = "0 so'm";
        return;
    }

    fetch(getApiBase() + '/api/user/balance', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Telegram-Init-Data': tg.initData || '',
        },
        body: JSON.stringify({ telegram_id: userId, initData: tg.initData || '' }),
    })
    .then(r => r.json())
    .then(data => {
        if (data.ok && data.balance !== undefined) {
            userBalance = data.balance;
            balanceElement.textContent = userBalance.toLocaleString('uz-UZ') + " so'm";
        }
    })
    .catch(() => {
        balanceElement.textContent = "0 so'm";
    });
}

function formatNumber(num) {
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
}

function getUsername(inputId) {
    const val = (document.getElementById(inputId || 'username')?.value || '').trim();
    if (!val || val === '@') return null;
    return val.startsWith('@') ? val : '@' + val;
}

function setBuyButtonLoading(btnId, loading) {
    const btn = document.getElementById(btnId || 'buyBtn');
    if (!btn) return;
    if (loading) {
        btn.dataset.originalText = btn.textContent;
        btn.disabled = true;
        btn.textContent = 'Yuborilmoqda...';
    } else {
        btn.disabled = false;
        btn.textContent = btn.dataset.originalText || 'Sotib olish';
    }
}

/**
 * Submit order via HTTP POST to the API server.
 * Works with both inline and reply keyboard WebApp buttons.
 *
 * payload fields:
 *   action: 'buy_stars' | 'buy_premium' | 'buy_gift' | 'buy_phone'
 *   + action-specific fields (amount, username, duration, etc.)
 */
async function submitOrder(payload, btnId) {
    setBuyButtonLoading(btnId, true);

    // Map action → API endpoint
    const endpoints = {
        buy_stars:   '/api/order/stars',
        buy_premium: '/api/order/premium',
        buy_gift:    '/api/order/gift',
        buy_phone:   '/api/order/phone',
    };

    const endpoint = endpoints[payload.action];
    if (!endpoint) {
        setBuyButtonLoading(btnId, false);
        tg.showAlert('Noma\'lum buyurtma turi.');
        return;
    }

    // Build request body — rename fields to what the API expects
    const body = { ...payload };
    if (payload.action === 'buy_stars') {
        body.quantity = payload.amount;
    }
    if (payload.action === 'buy_premium') {
        body.months = payload.duration;
    }

    // Pass Telegram initData for auth
    body.initData = tg.initData || '';
    body.telegram_id = tg.initDataUnsafe?.user?.id || null;

    try {
        const response = await fetch(getApiBase() + endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Telegram-Init-Data': tg.initData || '',
            },
            body: JSON.stringify(body),
        });

        const result = await response.json();

        if (result.ok) {
            const successMessages = {
                buy_stars:   '⭐ Stars muvaffaqiyatli sotib olindi!',
                buy_premium: '💎 Premium obuna muvaffaqiyatli faollashtirildi!',
                buy_gift:    '🎁 Sovg\'a muvaffaqiyatli yuborildi!',
                buy_phone:   '📱 Virtual raqam muvaffaqiyatli olindi!',
            };
            tg.showPopup({
                title: '✅ Muvaffaqiyatli',
                message: successMessages[payload.action] || 'Buyurtma bajarildi!',
                buttons: [{ type: 'ok' }]
            }, () => tg.close());
        } else {
            setBuyButtonLoading(btnId, false);
            tg.showPopup({
                title: '❌ Xatolik',
                message: result.error || 'Qayta urinib ko\'ring',
                buttons: [{ type: 'close' }]
            });
        }
    } catch (e) {
        setBuyButtonLoading(btnId, false);
        tg.showPopup({
            title: '❌ Tarmoq xatoligi',
            message: e.message || 'Serverga ulanib bo\'lmadi. Qayta urinib ko\'ring.',
            buttons: [{ type: 'close' }]
        });
    }
}

function setupPurchaseButton(onClick, text) {
    const label = text || 'Sotib olish';
    const btn = document.getElementById('buyBtn');
    if (!btn) return;

    btn.disabled = false;
    btn.textContent = label;
    btn.onclick = onClick;

    if (tg.MainButton) {
        tg.MainButton.hide();
    }
}

// ===== LOADER =====
function showLoader(text) {
  const overlay = document.getElementById('loaderOverlay');
  if (!overlay) return;
  const sub = overlay.querySelector('.loader-sub');
  if (sub && text) sub.textContent = text;
  overlay.classList.remove('hidden');
}

function hideLoader() {
  const overlay = document.getElementById('loaderOverlay');
  if (!overlay) return;
  overlay.classList.add('hidden');
}

function validateStarsAmount(amount) {
    const n = parseInt(amount, 10);
    if (isNaN(n) || n < STARS_MIN) {
        return { ok: false, message: `Minimal miqdor: ${STARS_MIN} stars` };
    }
    if (n > STARS_MAX) {
        return { ok: false, message: `Maksimal miqdor: ${STARS_MAX.toLocaleString('uz-UZ')} stars` };
    }
    return { ok: true, value: n };
}
