const alertTypeLabels = {
    'looking_down': 'Olhando para baixo',
    'eyes_closed': 'Olhos fechados',
    'phone_usage': 'Usando celular',
    'inattention': 'Desatenção prolongada',
    'distracted': 'Distraído',
    'possivel_sonolencia': 'Possível Sonolência',
    'atencao': 'Atenção: sinais iniciais de sonolência',
    'sonolencia': 'Sonolência',
    'microssono': 'Microssono (olhos fechados 1 s)',
    'sono': 'Sono (olhos fechados 3 s)',
    'nao_responsivo': 'Sem resposta (olhos fechados 6 s)',
    'rosto_nao_detectado': 'Câmera sem visão do rosto',
    'calibracao_concluida': 'Calibração concluída',
    'calibracao_suspeita': 'Calibração suspeita (motorista já cansado?)',
    'sonolencia_abrupta': 'Sonolência abrupta (queda rápida do estado de alerta)',
    'ativacao_atipica': 'Sinais compatíveis com ativação atípica (não é diagnóstico)',
    'direcao_continua': 'Direção contínua acima de 5 h 30 min',
    'olhos_nao_visiveis': 'Olhos não visíveis (óculos escuros ou fora da imagem)',
    'celular_na_mao': 'Celular na mão',
    'celular_no_ouvido': 'Celular no ouvido',
    'olhando_celular': 'Olhando o celular (mais de 2 s)'
};

const REFRESH_MS = 30000;

function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, (char) => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[char]));
}

function formatDateTime(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleString('pt-BR', {
        timeZone: 'America/Sao_Paulo',
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

async function fetchJson(url) {
    const response = await fetch(url);
    if (!response.ok) {
        throw new Error(`${url} respondeu HTTP ${response.status}`);
    }
    return response.json();
}

function setText(id, value) {
    const element = document.getElementById(id);
    if (element) element.textContent = value;
}

function currentFilters() {
    const params = new URLSearchParams();
    const fields = {
        start: 'filter-start',
        end: 'filter-end',
        vehicle_id: 'filter-vehicle',
        device_id: 'filter-device'
    };
    for (const [param, id] of Object.entries(fields)) {
        const value = document.getElementById(id).value;
        if (value) params.set(param, value);
    }
    return params;
}

function fillSelect(id, options, emptyLabel) {
    const select = document.getElementById(id);
    const selected = select.value;
    select.innerHTML = `<option value="">${escapeHtml(emptyLabel)}</option>` +
        options.map(([value, label]) => `<option value="${escapeHtml(value)}">${escapeHtml(label)}</option>`).join('');
    select.value = selected;
}

async function fetchDashboardStats() {
    try {
        updateDashboard(await fetchJson('/api/dashboard/stats'));
    } catch (error) {
        console.error('Erro ao carregar estatísticas:', error);
    }
}

function updateDashboard(stats) {
    setText('total-drivers', stats.total_drivers);
    setText('total-vehicles', stats.total_vehicles);
    setText('total-alerts-today', stats.total_alerts_today);
    setText('high-risk-alerts', stats.high_risk_alerts);
    setText('monitoring-count', `${stats.online_devices}/${stats.total_devices}`);

    const offline = stats.total_devices - stats.online_devices;
    if (stats.total_devices === 0) {
        setText('fleet-status', 'Sem dispositivos');
    } else {
        setText('fleet-status', offline > 0 ? `${offline} offline` : 'Normal');
    }

    const last = stats.recent_alerts[0];
    setText('last-alert', last
        ? `${last.timestamp_brazil} · ${last.vehicle_plate || last.device_name || 'sem veículo'}`
        : 'Nenhuma');
    setText('top-driver', stats.top_driver_name
        ? `${stats.top_driver_name} (${stats.top_driver_alerts})`
        : 'Nenhum');
}

async function loadDevices() {
    try {
        const devices = await fetchJson('/api/devices');
        renderDevices(devices);
        fillSelect('filter-device', devices.map((device) => [device.id, device.name]), 'Todos os dispositivos');
    } catch (error) {
        console.error('Erro ao carregar dispositivos:', error);
    }
}

function renderDevices(devices) {
    const tbody = document.getElementById('devices-table-body');

    if (devices.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="loading">Nenhum dispositivo cadastrado. No servidor: python manage.py criar-dispositivo --nome "Nome"</td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = devices.map((device) => {
        let status = device.online
            ? '<span class="status-badge">Online</span>'
            : '<span class="status-badge offline">Offline</span>';
        if (device.revoked) status = '<span class="status-badge revoked">Revogado</span>';

        let camera = '—';
        if (device.camera_ok === true) camera = 'OK';
        if (device.camera_ok === false) camera = '<span class="text-danger">Falha</span>';

        return `
            <tr>
                <td>${escapeHtml(device.name)}<div class="muted">${escapeHtml(device.hostname || device.token_prefix + '…')}</div></td>
                <td>${escapeHtml(device.vehicle_plate || '—')}</td>
                <td>${escapeHtml(device.driver_name || '—')}</td>
                <td>${status}</td>
                <td>${escapeHtml(device.last_seen_local || 'Nunca conectou')}</td>
                <td>${device.pending_events}</td>
                <td>${camera}</td>
            </tr>
        `;
    }).join('');
}

async function loadVehicles() {
    try {
        const vehicles = await fetchJson('/api/vehicles');
        fillSelect('filter-vehicle', vehicles.map((vehicle) => [vehicle.id, vehicle.plate]), 'Todos os veículos');
    } catch (error) {
        console.error('Erro ao carregar veículos:', error);
    }
}

async function loadAlerts() {
    const params = currentFilters();
    params.set('limit', '200');
    try {
        updateAlertsTable(await fetchJson(`/api/alerts?${params}`));
    } catch (error) {
        console.error('Erro ao carregar alertas:', error);
    }
}

function updateAlertsTable(alerts) {
    const tbody = document.getElementById('alerts-table-body');

    if (!alerts || alerts.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="loading">Nenhum alerta encontrado</td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = alerts.map((alert) => `
        <tr>
            <td>${escapeHtml(alert.driver_name || (alert.driver_id ? 'Motorista ' + alert.driver_id : '—'))}</td>
            <td>${escapeHtml(alert.vehicle_plate || (alert.vehicle_id ? 'Veículo ' + alert.vehicle_id : '—'))}</td>
            <td>${escapeHtml(alert.device_name || '—')}</td>
            <td>${escapeHtml(alertTypeLabels[alert.alert_type] || alert.alert_type)}</td>
            <td>${escapeHtml(alert.timestamp_brazil || formatDateTime(alert.timestamp))}</td>
            <td>${alert.duration.toFixed(1)}s</td>
        </tr>
    `).join('');
}

function exportCsv() {
    window.location.href = `/api/alerts/export.csv?${currentFilters()}`;
}

function refreshAll() {
    fetchDashboardStats();
    loadDevices();
    loadAlerts();
}

function initWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        console.log('WebSocket connected');
    };

    ws.onmessage = (event) => {
        try {
            const message = JSON.parse(event.data);
            if (message.type === 'new_alert') {
                console.log('New alert received:', message.data);

                if (Notification.permission === 'granted') {
                    new Notification('Novo Alerta DriveSafe AI!', {
                        body: `${alertTypeLabels[message.data.alert_type] || message.data.alert_type}`,
                        icon: '/static/favicon.png'
                    });
                }

                refreshAll();
            }
        } catch (error) {
            console.error('Error processing WebSocket message:', error);
        }
    };

    ws.onclose = () => {
        console.log('WebSocket disconnected, reconnecting in 3s...');
        setTimeout(initWebSocket, 3000);
    };

    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
    };
}

if ('Notification' in window && Notification.permission === 'default') {
    Notification.requestPermission();
}

document.addEventListener('DOMContentLoaded', () => {
    loadVehicles();
    refreshAll();
    initWebSocket();

    document.getElementById('filters-form').addEventListener('submit', (event) => {
        event.preventDefault();
        loadAlerts();
    });
    document.getElementById('btn-clear').addEventListener('click', () => {
        document.getElementById('filters-form').reset();
        loadAlerts();
    });
    document.getElementById('btn-export').addEventListener('click', exportCsv);

    setInterval(refreshAll, REFRESH_MS);
});

function loadData() {
    refreshAll();
}
