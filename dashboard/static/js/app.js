const alertTypeLabels = {
    'looking_down': 'Olhando para baixo',
    'eyes_closed': 'Olhos fechados',
    'phone_usage': 'Usando celular',
    'inattention': 'Desatenção prolongada',
    'distracted': 'Distraído',
    'possivel_sonolencia': 'Possível Sonolência'
};

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

async function fetchDashboardStats() {
    try {
        const response = await fetch('/api/dashboard/stats');
        const data = await response.json();
        updateDashboard(data);
    } catch (error) {
        console.error('Error fetching stats:', error);
    }
}

function updateDashboard(stats) {
    const totalDriversEl = document.getElementById('total-drivers');
    const totalVehiclesEl = document.getElementById('total-vehicles');
    const totalAlertsTodayEl = document.getElementById('total-alerts-today');
    const highRiskAlertsEl = document.getElementById('high-risk-alerts');

    if (totalDriversEl) totalDriversEl.textContent = stats.total_drivers;
    if (totalVehiclesEl) totalVehiclesEl.textContent = stats.total_vehicles;
    if (totalAlertsTodayEl) totalAlertsTodayEl.textContent = stats.total_alerts_today;
    if (highRiskAlertsEl) highRiskAlertsEl.textContent = stats.high_risk_alerts;

    updateAlertsTable(stats.recent_alerts);
}

function updateAlertsTable(alerts) {
    const tbody = document.getElementById('alerts-table-body');
    
    if (!alerts || alerts.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="loading">Nenhum alerta registrado</td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = alerts.map(alert => `
        <tr>
            <td>${alert.driver_name || 'Motorista ' + alert.driver_id}</td>
            <td>${alert.vehicle_plate || 'Veículo ' + alert.vehicle_id}</td>
            <td>${alertTypeLabels[alert.alert_type] || alert.alert_type}</td>
            <td>${alert.timestamp_brazil || formatDateTime(alert.timestamp)}</td>
            <td>${alert.duration.toFixed(1)}s</td>
            <td>
                <span class="status-badge">Registrado</span>
            </td>
        </tr>
    `).join('');
}

async function loadAllAlerts() {
    try {
        const response = await fetch('/api/alerts');
        const alerts = await response.json();
        updateAlertsTable(alerts);
    } catch (error) {
        console.error('Error loading alerts:', error);
    }
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
                
                fetchDashboardStats();
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
    fetchDashboardStats();
    initWebSocket();
    
    setInterval(fetchDashboardStats, 30000);
});

function loadData() {
    loadAllAlerts();
}
