/* Users Page */
let usersPage = 1;
let usersQuery = '';
let usersSearchBy = 'telegram_id';

async function loadUsers() {
    const content = document.getElementById('mainContent');
    usersPage = 1;
    
    content.innerHTML = `
        <div class="page-header">
            <div>
                <h1 class="page-title">👥 Пользователи</h1>
                <p class="page-subtitle">Управление пользователями StarPayUz</p>
            </div>
        </div>
        
        <div class="search-bar">
            <input type="text" class="form-input" id="userSearchInput" 
                   placeholder="Поиск..." value="${usersQuery}"
                   onkeydown="if(event.key==='Enter') searchUsers()">
            <select class="form-select" id="userSearchBy">
                <option value="telegram_id" ${usersSearchBy === 'telegram_id' ? 'selected' : ''}>Telegram ID</option>
                <option value="username" ${usersSearchBy === 'username' ? 'selected' : ''}>Username</option>
                <option value="sp_id" ${usersSearchBy === 'sp_id' ? 'selected' : ''}>SP ID</option>
            </select>
            <button class="btn btn-primary btn-sm" onclick="searchUsers()">🔍 Поиск</button>
            <button class="btn btn-outline btn-sm" onclick="loadUsers()">🔄 Все</button>
        </div>
        
        <div class="card">
            <div class="table-container">
                <div id="usersTableContent">
                    <div class="loading"><div class="loading-spinner"></div>Загрузка пользователей...</div>
                </div>
            </div>
            <div id="usersPagination" class="pagination"></div>
        </div>
    `;
    
    await fetchUsers();
}

function searchUsers() {
    usersQuery = document.getElementById('userSearchInput').value.trim();
    usersSearchBy = document.getElementById('userSearchBy').value;
    usersPage = 1;
    fetchUsers();
}

async function fetchUsers() {
    const tableContent = document.getElementById('usersTableContent');
    const pagination = document.getElementById('usersPagination');
    
    try {
        let url = `/api/admin/users?page=${usersPage}&page_size=20`;
        let data;
        
        if (usersQuery) {
            url = `/api/admin/users/search?query=${encodeURIComponent(usersQuery)}&search_by=${usersSearchBy}&page=${usersPage}&page_size=20`;
        }
        
        data = await apiGet(url);
        
        if (data.users.length === 0) {
            tableContent.innerHTML = `
                <div class="empty-state">
                    <div class="icon">🔍</div>
                    <h3>Пользователи не найдены</h3>
                    <p>Измените параметры поиска</p>
                </div>
            `;
            pagination.innerHTML = '';
            return;
        }
        
        tableContent.innerHTML = `
            <table class="data-table">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Пользователь</th>
                        <th>SP ID</th>
                        <th>Баланс</th>
                        <th>Статус</th>
                        <th>Рефералы</th>
                        <th>Дата</th>
                        <th>Действия</th>
                    </tr>
                </thead>
                <tbody>
                    ${data.users.map(u => `
                        <tr style="${u.is_blocked ? 'opacity:0.6;' : ''}">
                            <td><code>${u.telegram_id}</code></td>
                            <td>
                                <div class="user-cell">
                                    <div class="user-avatar">${(u.username || u.full_name || '?')[0].toUpperCase()}</div>
                                    <div>
                                        <div class="user-name">${u.full_name || '—'}</div>
                                        <div class="user-sub">${u.username ? '@' + u.username : '—'}</div>
                                    </div>
                                </div>
                            </td>
                            <td>#${u.sp_id || '—'}</td>
                            <td><strong>${formatNumber(u.balance)}</strong> so'm</td>
                            <td>
                                ${u.is_premium ? '<span class="badge premium-badge">⭐ Premium</span> ' : ''}
                                ${u.is_blocked ? '<span class="badge danger">🚫 Заблокирован</span>' : '<span class="badge success">✅ Активен</span>'}
                            </td>
                            <td>${u.referrals || 0}</td>
                            <td style="white-space:nowrap;">${formatDate(u.created_at)}</td>
                            <td>
                                <div style="display:flex;gap:4px;flex-wrap:wrap;">
                                    <button class="btn btn-outline btn-sm" onclick="showUserInfo(${u.telegram_id})" title="Просмотр">👁</button>
                                    <button class="btn btn-success btn-sm" onclick="quickAddBalance(${u.telegram_id})" title="Начислить баланс">➕</button>
                                    <button class="btn btn-danger btn-sm" onclick="quickDeductBalance(${u.telegram_id})" title="Списать баланс">➖</button>
                                    <button class="btn btn-warning btn-sm" onclick="quickResetBalance(${u.telegram_id})" title="Обнулить баланс">🔄</button>
                                    ${u.is_blocked 
                                        ? `<button class="btn btn-success btn-sm" onclick="confirmUnblockUser(${u.telegram_id})" title="Разблокировать">🔓</button>`
                                        : `<button class="btn btn-warning btn-sm" onclick="confirmBlockUser(${u.telegram_id})" title="Заблокировать">🔒</button>`
                                    }
                                    <button class="btn btn-danger btn-sm" onclick="confirmDeleteUser(${u.telegram_id})" title="Удалить">🗑</button>
                                </div>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
        
        const totalPages = Math.ceil(data.total / 20);
        renderUsersPagination(pagination, usersPage, totalPages);
        
    } catch (err) {
        tableContent.innerHTML = `<div class="alert danger">❌ ${err.message}</div>`;
    }
}

async function showUserInfo(telegramId) {
    try {
        const user = await apiGet(`/api/admin/users/${telegramId}`);
        
        showModal(`👤 Пользователь #${user.sp_id || user.telegram_id}`, `
            <div class="form-group">
                <label class="form-label">Telegram ID</label>
                <div class="form-input" style="background:var(--bg-secondary);cursor:default;"><code>${user.telegram_id}</code></div>
            </div>
            <div class="form-group">
                <label class="form-label">SP ID</label>
                <div class="form-input" style="background:var(--bg-secondary);cursor:default;">#${user.sp_id || '—'}</div>
            </div>
            <div class="form-group">
                <label class="form-label">Имя</label>
                <div class="form-input" style="background:var(--bg-secondary);cursor:default;">${user.full_name || '—'}</div>
            </div>
            <div class="form-group">
                <label class="form-label">Username</label>
                <div class="form-input" style="background:var(--bg-secondary);cursor:default;">${user.username ? '@' + user.username : '—'}</div>
            </div>
            <div class="form-group">
                <label class="form-label">Баланс</label>
                <div class="form-input" style="background:var(--bg-secondary);cursor:default;"><strong>${formatNumber(user.balance)} so'm</strong></div>
            </div>
            <div class="form-group">
                <label class="form-label">Статус</label>
                <div class="form-input" style="background:var(--bg-secondary);cursor:default;">
                    ${user.is_premium ? '⭐ Premium' : ''}
                    ${user.is_blocked ? '🚫 Заблокирован' : '✅ Активен'}
                </div>
            </div>
            <div class="form-group">
                <label class="form-label">Premium до</label>
                <div class="form-input" style="background:var(--bg-secondary);cursor:default;">${user.premium_until ? formatDate(user.premium_until) : '—'}</div>
            </div>
            <div class="form-group">
                <label class="form-label">Рефералы</label>
                <div class="form-input" style="background:var(--bg-secondary);cursor:default;">${user.referrals || 0} чел.</div>
            </div>
            <div class="form-group">
                <label class="form-label">Язык</label>
                <div class="form-input" style="background:var(--bg-secondary);cursor:default;">${user.language || 'uz'}</div>
            </div>
            <div class="form-group">
                <label class="form-label">Дата регистрации</label>
                <div class="form-input" style="background:var(--bg-secondary);cursor:default;">${formatDate(user.created_at)}</div>
            </div>
        `, '', null);
        
        let actionsHtml = `<button class="btn btn-outline" onclick="closeModal()">Закрыть</button>`;
        actionsHtml += `<button class="btn btn-success" onclick="closeModal();quickAddBalance(${telegramId})">➕ Начислить</button>`;
        actionsHtml += `<button class="btn btn-danger" onclick="closeModal();quickDeductBalance(${telegramId})">➖ Списать</button>`;
        actionsHtml += `<button class="btn btn-warning" onclick="closeModal();quickResetBalance(${telegramId})">🔄 Обнулить</button>`;
        if (user.is_blocked) {
            actionsHtml += `<button class="btn btn-success" onclick="closeModal();confirmUnblockUser(${telegramId})">🔓 Разблокировать</button>`;
        } else {
            actionsHtml += `<button class="btn btn-warning" onclick="closeModal();confirmBlockUser(${telegramId})">🔒 Заблокировать</button>`;
        }
        actionsHtml += `<button class="btn btn-danger" onclick="closeModal();confirmDeleteUser(${telegramId})">🗑 Удалить</button>`;
        document.getElementById('modalFooter').innerHTML = actionsHtml;
        
    } catch (err) {
        alert('Ошибка: ' + err.message);
    }
}

// Quick balance actions from users page
function quickAddBalance(telegramId) {
    showModal('➕ Начислить баланс пользователю #' + telegramId, `
        <div class="form-group">
            <label class="form-label">Telegram ID</label>
            <input type="text" class="form-input" value="${telegramId}" disabled style="background:var(--bg-secondary);">
        </div>
        <div class="form-group">
            <label class="form-label">Сумма (so'm)</label>
            <input type="number" class="form-input" id="quickBalanceAmount" placeholder="50000" min="1" required>
        </div>
        <div class="form-group">
            <label class="form-label">Причина</label>
            <textarea class="form-textarea" id="quickBalanceReason" placeholder="Например: бонус за активность"></textarea>
        </div>
    `, 'Начислить', async () => {
        const amount = parseInt(document.getElementById('quickBalanceAmount').value);
        const reason = document.getElementById('quickBalanceReason').value;
        if (!amount) { alert('Введите сумму'); return; }
        try {
            await apiPost('/api/admin/balance/add', { telegram_id: telegramId, amount, reason });
            alert('✅ Баланс успешно начислен');
            closeModal();
            fetchUsers();
        } catch (err) {
            alert('❌ ' + err.message);
        }
    });
}

function quickDeductBalance(telegramId) {
    showModal('➖ Списать баланс пользователя #' + telegramId, `
        <div class="form-group">
            <label class="form-label">Telegram ID</label>
            <input type="text" class="form-input" value="${telegramId}" disabled style="background:var(--bg-secondary);">
        </div>
        <div class="form-group">
            <label class="form-label">Сумма (so'm)</label>
            <input type="number" class="form-input" id="quickBalanceAmount" placeholder="10000" min="1" required>
        </div>
        <div class="form-group">
            <label class="form-label">Причина</label>
            <textarea class="form-textarea" id="quickBalanceReason" placeholder="Например: возврат средств"></textarea>
        </div>
    `, 'Списать', async () => {
        const amount = parseInt(document.getElementById('quickBalanceAmount').value);
        const reason = document.getElementById('quickBalanceReason').value;
        if (!amount) { alert('Введите сумму'); return; }
        try {
            await apiPost('/api/admin/balance/deduct', { telegram_id: telegramId, amount, reason });
            alert('✅ Баланс успешно списан');
            closeModal();
            fetchUsers();
        } catch (err) {
            alert('❌ ' + err.message);
        }
    });
}

function quickResetBalance(telegramId) {
    showModal('🔄 Обнулить баланс пользователя #' + telegramId, `
        <div class="form-group">
            <label class="form-label">Telegram ID</label>
            <input type="text" class="form-input" value="${telegramId}" disabled style="background:var(--bg-secondary);">
        </div>
        <div class="form-group">
            <label class="form-label">Причина</label>
            <textarea class="form-textarea" id="quickBalanceReason" placeholder="Например: сброс тестового баланса"></textarea>
        </div>
        <div class="alert warning">⚠️ Баланс пользователя будет сброшен до 0. Это действие нельзя отменить.</div>
    `, 'Обнулить', async () => {
        const reason = document.getElementById('quickBalanceReason').value;
        if (!confirm('Вы уверены, что хотите обнулить баланс пользователя ' + telegramId + '?')) return;
        try {
            await apiPost('/api/admin/balance/reset', { telegram_id: telegramId, reason });
            alert('✅ Баланс успешно обнулен');
            closeModal();
            fetchUsers();
        } catch (err) {
            alert('❌ ' + err.message);
        }
    });
}

function confirmBlockUser(telegramId) {
    if (confirm(`Заблокировать пользователя ${telegramId}?`)) {
        apiPost(`/api/admin/users/${telegramId}/block`, {})
            .then(() => { alert('✅ Пользователь заблокирован'); fetchUsers(); })
            .catch(err => alert('❌ ' + err.message));
    }
}

function confirmUnblockUser(telegramId) {
    if (confirm(`Разблокировать пользователя ${telegramId}?`)) {
        apiPost(`/api/admin/users/${telegramId}/unblock`, {})
            .then(() => { alert('✅ Пользователь разблокирован'); fetchUsers(); })
            .catch(err => alert('❌ ' + err.message));
    }
}

function confirmDeleteUser(telegramId) {
    if (confirm(`Вы уверены, что хотите удалить пользователя ${telegramId}? Это действие нельзя отменить!`)) {
        apiDelete(`/api/admin/users/${telegramId}`)
            .then(() => { alert('✅ Пользователь удален'); fetchUsers(); })
            .catch(err => alert('❌ ' + err.message));
    }
}

function renderUsersPagination(container, current, total) {
    if (total <= 1) { container.innerHTML = ''; return; }
    let html = '';
    html += `<button class="page-btn" onclick="usersPage=${current-1};fetchUsers()" ${current <= 1 ? 'disabled' : ''}>‹</button>`;
    const start = Math.max(1, current - 2);
    const end = Math.min(total, current + 2);
    if (start > 1) {
        html += `<button class="page-btn" onclick="usersPage=1;fetchUsers()">1</button>`;
        if (start > 2) html += `<span class="page-info">...</span>`;
    }
    for (let i = start; i <= end; i++) {
        html += `<button class="page-btn ${i === current ? 'active' : ''}" onclick="usersPage=${i};fetchUsers()">${i}</button>`;
    }
    if (end < total) {
        if (end < total - 1) html += `<span class="page-info">...</span>`;
        html += `<button class="page-btn" onclick="usersPage=${total};fetchUsers()">${total}</button>`;
    }
    html += `<button class="page-btn" onclick="usersPage=${current+1};fetchUsers()" ${current >= total ? 'disabled' : ''}>›</button>`;
    container.innerHTML = html;
}
