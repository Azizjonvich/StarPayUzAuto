// StarPayUz - Common JavaScript Functions

const STARS_MIN = 50;
const STARS_MAX = 1000000;

const tg = window.Telegram.WebApp;
tg.expand();
tg.ready();
tg.setHeaderColor('#0F1419');
tg.setBackgroundColor('#0F1419');

// User balance
let userBalance = 0;

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    loadUserBalance();
});

// Load user balance
function loadUserBalance() {
    const balanceElement = document.getElementById('balance');
    if (balanceElement) {
        // TODO: Load from server
        userBalance = 0;
        balanceElement.textContent = userBalance.toLocaleString('uz-UZ') + ' so\'m';
    }
}

// Format number with spaces
function formatNumber(num) {
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, " ");
}

// Show loading
function showLoading() {
    tg.MainButton.showProgress();
}

// Hide loading
function hideLoading() {
    tg.MainButton.hideProgress();
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
