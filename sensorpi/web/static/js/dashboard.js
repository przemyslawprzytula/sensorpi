/**
 * SensorPi Dashboard JavaScript
 * Handles WebSocket connection, data fetching, and UI updates
 */

// Configuration
const API_BASE = '';  // Same origin
let ws = null;
let charts = {};
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 10;

// ============== WebSocket Connection ==============

function connectWebSocket() {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/ws`;

    updateConnectionStatus('connecting');

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        console.log('WebSocket connected');
        updateConnectionStatus('connected');
        reconnectAttempts = 0;
    };

    ws.onclose = () => {
        console.log('WebSocket disconnected');
        updateConnectionStatus('disconnected');
        attemptReconnect();
    };

    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
    };

    ws.onmessage = (event) => {
        try {
            const message = JSON.parse(event.data);
            handleWebSocketMessage(message);
        } catch (e) {
            console.error('Failed to parse WebSocket message:', e);
        }
    };
}

function attemptReconnect() {
    if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
        showToast('Connection lost. Please refresh the page.', 'error');
        return;
    }

    reconnectAttempts++;
    const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000);
    console.log(`Reconnecting in ${delay}ms (attempt ${reconnectAttempts})`);

    setTimeout(connectWebSocket, delay);
}

function handleWebSocketMessage(message) {
    switch (message.type) {
        case 'sensor_update':
            handleSensorUpdate(message.data);
            break;
        case 'relay_update':
            handleRelayUpdate(message.data);
            break;
        case 'ping':
            ws.send(JSON.stringify({ type: 'pong' }));
            break;
        default:
            console.log('Unknown message type:', message.type);
    }
}

function updateConnectionStatus(status) {
    const dot = document.getElementById('connection-status');
    const text = document.getElementById('status-text');

    dot.className = 'status-dot ' + status;
    text.textContent = status.charAt(0).toUpperCase() + status.slice(1);
}

// ============== Data Fetching ==============

async function fetchAPI(endpoint) {
    try {
        const response = await fetch(`${API_BASE}/api${endpoint}`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return await response.json();
    } catch (error) {
        console.error(`API fetch error (${endpoint}):`, error);
        throw error;
    }
}

async function postAPI(endpoint, data) {
    try {
        const response = await fetch(`${API_BASE}/api${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return await response.json();
    } catch (error) {
        console.error(`API post error (${endpoint}):`, error);
        throw error;
    }
}

// ============== System Status ==============

async function loadSystemStatus() {
    try {
        const status = await fetchAPI('/status');

        document.getElementById('rpi-status').textContent = status.rpi_connected ? 'Connected' : 'Disconnected';
        document.getElementById('rpi-status').className = 'value ' + (status.rpi_connected ? 'status-ok' : 'status-error');

        document.getElementById('db-status').textContent = status.database_connected ? 'Connected' : 'Error';
        document.getElementById('db-status').className = 'value ' + (status.database_connected ? 'status-ok' : 'status-error');

        document.getElementById('reading-count').textContent = status.reading_count.toLocaleString();

        if (status.last_reading_at) {
            const date = new Date(status.last_reading_at);
            document.getElementById('last-reading').textContent = formatRelativeTime(date);
        }

        document.getElementById('automation-enabled').checked = status.automation_enabled;
    } catch (error) {
        showToast('Failed to load system status', 'error');
    }
}

// ============== Sensors ==============

async function loadSensors() {
    try {
        const sensors = await fetchAPI('/sensors');
        renderSensorCards(sensors);
    } catch (error) {
        showToast('Failed to load sensors', 'error');
    }
}

function renderSensorCards(sensors) {
    const container = document.getElementById('sensor-cards');
    container.innerHTML = '';

    sensors.forEach(sensor => {
        const card = document.createElement('div');
        card.className = `sensor-card ${sensor.sensor_type}`;
        card.id = `sensor-${sensor.sensor_id}`;

        const value = sensor.latest_value !== null ? sensor.latest_value.toFixed(1) : '--';
        const time = sensor.latest_recorded_at
            ? formatRelativeTime(new Date(sensor.latest_recorded_at))
            : 'No data';

        card.innerHTML = `
            <div class="sensor-name">${formatSensorType(sensor.sensor_type)}</div>
            <div class="sensor-value">${value}<span class="sensor-unit">${sensor.unit}</span></div>
            <div class="sensor-location">${sensor.location || 'Unknown'}</div>
            <div class="sensor-time">${time}</div>
        `;

        container.appendChild(card);
    });
}

function handleSensorUpdate(data) {
    const card = document.getElementById(`sensor-${data.sensor_id}`);
    if (card) {
        const valueEl = card.querySelector('.sensor-value');
        const timeEl = card.querySelector('.sensor-time');

        valueEl.innerHTML = `${data.value.toFixed(1)}<span class="sensor-unit">${data.unit}</span>`;
        timeEl.textContent = 'Just now';

        // Flash effect
        card.style.animation = 'none';
        card.offsetHeight; // Trigger reflow
        card.style.animation = 'pulse 0.5s';
    }

    // Update chart if visible
    updateChartWithNewReading(data);
}

// ============== Charts ==============

async function loadCharts() {
    const hours = parseInt(document.getElementById('chart-timespan').value);

    try {
        const sensors = await fetchAPI('/sensors');

        // Temperature chart
        const tempSensors = sensors.filter(s => s.sensor_type === 'temperature');
        await loadTemperatureChart(tempSensors, hours);

        // Light chart
        const lightSensors = sensors.filter(s => s.sensor_type === 'light');
        await loadLightChart(lightSensors, hours);
    } catch (error) {
        showToast('Failed to load chart data', 'error');
    }
}

async function loadTemperatureChart(sensors, hours) {
    const ctx = document.getElementById('temperature-chart');
    if (!ctx) return;

    const datasets = await Promise.all(sensors.map(async (sensor, index) => {
        const data = await fetchAPI(`/sensors/${sensor.sensor_id}/timeseries?hours=${hours}`);
        return {
            label: `${sensor.sensor_id} (${sensor.location || 'Unknown'})`,
            data: data.data.map(d => ({ x: new Date(d.timestamp), y: d.value })),
            borderColor: getChartColor(index),
            backgroundColor: getChartColor(index, 0.1),
            fill: false,
            tension: 0.3,
        };
    }));

    if (charts.temperature) {
        charts.temperature.destroy();
    }

    charts.temperature = new Chart(ctx, {
        type: 'line',
        data: { datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Temperature',
                    color: '#eee',
                },
                legend: {
                    labels: { color: '#aaa' },
                },
            },
            scales: {
                x: {
                    type: 'time',
                    time: { unit: hours <= 6 ? 'minute' : 'hour' },
                    ticks: { color: '#aaa' },
                    grid: { color: 'rgba(255,255,255,0.1)' },
                },
                y: {
                    title: { display: true, text: 'C', color: '#aaa' },
                    ticks: { color: '#aaa' },
                    grid: { color: 'rgba(255,255,255,0.1)' },
                },
            },
        },
    });
}

async function loadLightChart(sensors, hours) {
    const ctx = document.getElementById('light-chart');
    if (!ctx) return;

    const datasets = await Promise.all(sensors.map(async (sensor, index) => {
        const data = await fetchAPI(`/sensors/${sensor.sensor_id}/timeseries?hours=${hours}`);
        return {
            label: `${sensor.sensor_id} (${sensor.location || 'Unknown'})`,
            data: data.data.map(d => ({ x: new Date(d.timestamp), y: d.value })),
            borderColor: '#ffd43b',
            backgroundColor: 'rgba(255, 212, 59, 0.1)',
            fill: true,
            tension: 0.3,
        };
    }));

    if (charts.light) {
        charts.light.destroy();
    }

    charts.light = new Chart(ctx, {
        type: 'line',
        data: { datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Light Level',
                    color: '#eee',
                },
                legend: {
                    labels: { color: '#aaa' },
                },
            },
            scales: {
                x: {
                    type: 'time',
                    time: { unit: hours <= 6 ? 'minute' : 'hour' },
                    ticks: { color: '#aaa' },
                    grid: { color: 'rgba(255,255,255,0.1)' },
                },
                y: {
                    title: { display: true, text: 'lux', color: '#aaa' },
                    ticks: { color: '#aaa' },
                    grid: { color: 'rgba(255,255,255,0.1)' },
                },
            },
        },
    });
}

function updateChartWithNewReading(data) {
    // Add new point to appropriate chart
    const chart = data.sensor_type === 'temperature' ? charts.temperature : charts.light;
    if (!chart) return;

    const dataset = chart.data.datasets.find(ds => ds.label.startsWith(data.sensor_id));
    if (dataset) {
        dataset.data.push({ x: new Date(data.recorded_at), y: data.value });
        chart.update('quiet');
    }
}

function getChartColor(index, alpha = 1) {
    const colors = [
        `rgba(255, 107, 107, ${alpha})`,
        `rgba(77, 171, 247, ${alpha})`,
        `rgba(145, 230, 160, ${alpha})`,
        `rgba(255, 183, 77, ${alpha})`,
    ];
    return colors[index % colors.length];
}

// ============== Relays ==============

async function loadRelays() {
    try {
        const data = await fetchAPI('/relays');
        renderRelayCards(data.relays);
        renderDependencyInfo(data.dependencies);
    } catch (error) {
        const container = document.getElementById('relay-grid');
        container.innerHTML = '<p class="error">RPi API unavailable. Cannot control relays.</p>';
    }
}

function renderRelayCards(relays) {
    const container = document.getElementById('relay-grid');
    container.innerHTML = '';

    relays.forEach(relay => {
        const card = document.createElement('div');
        card.className = 'relay-card';
        card.id = `relay-${relay.id}`;

        const isOn = relay.state === 'on';

        card.innerHTML = `
            <div class="relay-name">${relay.name}</div>
            <div class="relay-id">${relay.id}</div>
            <label class="relay-toggle">
                <input type="checkbox" ${isOn ? 'checked' : ''} data-relay-id="${relay.id}">
                <span class="toggle-btn"></span>
            </label>
            <div class="relay-status ${relay.state}">${relay.state.toUpperCase()}</div>
        `;

        const checkbox = card.querySelector('input[type="checkbox"]');
        checkbox.addEventListener('change', (e) => toggleRelay(relay.id, e.target.checked));

        container.appendChild(card);
    });
}

function renderDependencyInfo(dependencies) {
    const container = document.getElementById('relay-dependencies');
    if (!dependencies || Object.keys(dependencies).length === 0) {
        container.innerHTML = '';
        return;
    }

    let html = '<strong>Dependencies:</strong><ul>';
    for (const [device, config] of Object.entries(dependencies)) {
        if (config.required_by) {
            html += `<li><strong>${device}</strong> is required by: ${config.required_by.join(', ')}</li>`;
        }
        if (config.requires) {
            html += `<li><strong>${device}</strong> requires: ${config.requires.join(', ')}</li>`;
        }
    }
    html += '</ul>';
    container.innerHTML = html;
}

async function toggleRelay(relayId, state) {
    const card = document.getElementById(`relay-${relayId}`);
    const checkbox = card.querySelector('input[type="checkbox"]');
    const statusEl = card.querySelector('.relay-status');

    checkbox.disabled = true;

    try {
        await postAPI(`/relays/${relayId}`, { state: state ? 'on' : 'off' });
        statusEl.textContent = state ? 'ON' : 'OFF';
        statusEl.className = 'relay-status ' + (state ? 'on' : 'off');
        showToast(`${relayId} turned ${state ? 'ON' : 'OFF'}`, 'success');
    } catch (error) {
        checkbox.checked = !state; // Revert
        showToast(`Failed to toggle ${relayId}`, 'error');
    } finally {
        checkbox.disabled = false;
    }
}

function handleRelayUpdate(data) {
    if (data.emergency_stop) {
        loadRelays(); // Reload all
        showToast('Emergency stop activated!', 'warning');
        return;
    }

    const card = document.getElementById(`relay-${data.relay_id}`);
    if (card) {
        const checkbox = card.querySelector('input[type="checkbox"]');
        const statusEl = card.querySelector('.relay-status');

        checkbox.checked = data.state === 'on';
        statusEl.textContent = data.state.toUpperCase();
        statusEl.className = 'relay-status ' + data.state;
    }
}

async function emergencyStop() {
    if (!confirm('This will turn OFF all relays. Continue?')) return;

    try {
        await postAPI('/relays/emergency-stop');
        showToast('All relays turned OFF', 'warning');
        loadRelays();
    } catch (error) {
        showToast('Emergency stop failed!', 'error');
    }
}

// ============== Automation ==============

async function loadAutomation() {
    try {
        const config = await fetchAPI('/automation');
        document.getElementById('automation-enabled').checked = config.enabled;
        renderRules(config.rules);
    } catch (error) {
        console.error('Failed to load automation config:', error);
    }
}

function renderRules(rules) {
    const container = document.getElementById('rules-list');
    container.innerHTML = '';

    if (!rules || rules.length === 0) {
        container.innerHTML = '<p class="no-data">No automation rules configured.</p>';
        return;
    }

    rules.forEach(rule => {
        const item = document.createElement('div');
        item.className = 'rule-item' + (rule.is_active ? '' : ' inactive');

        const conditions = rule.conditions.map(c =>
            `${c.sensor_type} ${c.operator} ${c.threshold}`
        ).join(' AND ');

        item.innerHTML = `
            <div>
                <div class="rule-name">${rule.name}</div>
                <div class="rule-condition">When: ${conditions}</div>
            </div>
            <div class="rule-target">-&gt; ${rule.device_id}</div>
        `;

        container.appendChild(item);
    });
}

// ============== Utilities ==============

function formatSensorType(type) {
    const names = {
        temperature: 'Temperature',
        humidity: 'Humidity',
        light: 'Light',
    };
    return names[type] || type;
}

function formatRelativeTime(date) {
    const seconds = Math.floor((new Date() - date) / 1000);

    if (seconds < 60) return 'Just now';
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    return `${Math.floor(seconds / 86400)}d ago`;
}

function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.remove();
    }, 3000);
}

// ============== Event Listeners ==============

document.addEventListener('DOMContentLoaded', () => {
    // Initial load
    loadSystemStatus();
    loadSensors();
    loadCharts();
    loadRelays();
    loadAutomation();

    // Connect WebSocket
    connectWebSocket();

    // Timespan selector
    document.getElementById('chart-timespan').addEventListener('change', loadCharts);

    // Emergency stop button
    document.getElementById('emergency-stop').addEventListener('click', emergencyStop);

    // Refresh status periodically
    setInterval(loadSystemStatus, 30000);
});

// Keep WebSocket alive
setInterval(() => {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'ping' }));
    }
}, 25000);
