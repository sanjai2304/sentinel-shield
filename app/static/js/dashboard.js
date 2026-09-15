/**
 * SentinelShield Live SOC Command Center Controller.
 * Manages WebSockets, real-time data feeds, UI modals, RBAC switching, and attack triggers.
 */

class SentinelDashboard {
  constructor() {
    this.ws = null;
    this.reconnectTimer = null;
    this.isMuted = false;
    
    // Auth & Identity state
    this.currentUser = {
      username: 'admin',
      role: 'admin',
      token: null,
    };

    // Preset credential tokens for frictionless RBAC demo
    this.credentials = {
      'admin': { password: 'AdminSecret123!', role: 'admin' },
      'analyst_bob': { password: 'AnalystBob123!', role: 'analyst' },
      'analyst_alice': { password: 'AnalystAlice123!', role: 'analyst' },
      'analyst_carol': { password: 'AnalystCarol123!', role: 'analyst' },
    };

    // Telemetry aggregations
    this.stats = {
      totalRequests: 0,
      totalAnomalies: 0,
      criticalAnomalies: 0,
      recentWindowReqs: 0,
      recentWindowAnoms: 0,
      classifications: { INTERNAL: 0, CONFIDENTIAL: 0, RESTRICTED: 0, TOP_SECRET: 0 },
    };

    // Submodules
    this.graphVis = null;
    this.charts = null;

    this.init();
  }

  async init() {
    // 1. Authenticate default user
    await this.authenticate('admin');

    // 2. Initialize visualizers
    this.graphVis = new BipartiteGraphVisualizer('networkCanvas');
    this.charts = new DashboardCharts();

    // 3. Connect WebSocket
    this.connectWebSocket();

    // 4. Bind UI DOM events
    this.bindEvents();

    // 5. Periodic chart aggregator
    setInterval(() => {
      if (this.charts) {
        this.charts.pushDataPoint(this.stats.recentWindowReqs, this.stats.recentWindowAnoms);
        this.stats.recentWindowReqs = 0;
        this.stats.recentWindowAnoms = 0;
      }
    }, 5000);
  }

  async authenticate(username) {
    const cred = this.credentials[username];
    if (!cred) return;

    try {
      const res = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password: cred.password }),
      });

      if (!res.ok) {
        console.error('Authentication failed:', await res.text());
        return;
      }

      const data = await res.json();
      this.currentUser = {
        username: data.username,
        role: data.role,
        department: data.department,
        token: data.access_token,
      };

      this.updateUserUI();
    } catch (e) {
      console.error('Error authenticating:', e);
    }
  }

  updateUserUI() {
    const userSelect = document.getElementById('userSelect');
    if (userSelect) userSelect.value = this.currentUser.username;

    const roleBadge = document.getElementById('roleBadge');
    if (roleBadge) {
      roleBadge.textContent = this.currentUser.role.toUpperCase();
      roleBadge.className = `role-badge ${this.currentUser.role}`;
    }

    // Toggle admin-only buttons or warnings
    const adminOnlyBtns = document.querySelectorAll('.admin-only');
    adminOnlyBtns.forEach(btn => {
      btn.style.opacity = this.currentUser.role === 'admin' ? '1' : '0.4';
      btn.title = this.currentUser.role === 'admin' ? '' : 'Requires Admin role';
    });
  }

  connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/dashboard`;

    this.updateWsStatus(false);
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log('Connected to SentinelShield WebSocket stream.');
      this.updateWsStatus(true);
      if (this.reconnectTimer) {
        clearInterval(this.reconnectTimer);
        this.reconnectTimer = null;
      }
    };

    this.ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        this.handleStreamMessage(msg);
      } catch (e) {
        console.error('Error parsing WebSocket message:', e);
      }
    };

    this.ws.onclose = () => {
      console.warn('WebSocket connection lost. Reconnecting in 3s...');
      this.updateWsStatus(false);
      if (!this.reconnectTimer) {
        this.reconnectTimer = setInterval(() => this.connectWebSocket(), 3000);
      }
    };

    this.ws.onerror = (err) => {
      console.error('WebSocket error:', err);
    };
  }

  updateWsStatus(connected) {
    const statusText = document.getElementById('statusText');
    const statusDot = document.getElementById('statusDot');
    if (statusText) statusText.textContent = connected ? 'STREAMING REAL-TIME' : 'RECONNECTING...';
    if (statusDot) statusDot.style.backgroundColor = connected ? '#10b981' : '#f59e0b';
  }

  handleStreamMessage(msg) {
    const type = msg.type;
    const data = msg.data;

    switch (type) {
      case 'INITIAL_STATE':
        this.handleInitialState(data);
        break;
      case 'ACCESS_EVENT':
        this.handleAccessEvent(data);
        break;
      case 'ANOMALY_ALERT':
        this.handleAnomalyAlert(data);
        break;
      case 'TOPOLOGY_UPDATE':
        if (this.graphVis) this.graphVis.updateTopology(data);
        break;
      default:
        break;
    }
  }

  handleInitialState(data) {
    if (data.topology && this.graphVis) {
      this.graphVis.updateTopology(data.topology);
    }

    if (data.cumulative) {
      this.stats.totalRequests = data.cumulative.total_events || 0;
      this.stats.totalAnomalies = data.cumulative.total_anomalies || 0;
    } else {
      this.stats.totalRequests = (data.recent_events || []).length;
      this.stats.totalAnomalies = (data.recent_anomalies || []).length;
    }

    if (data.recent_anomalies) {
      const feed = document.getElementById('anomalyFeed');
      if (feed) feed.innerHTML = '';
      data.recent_anomalies.forEach(anom => this.renderAnomalyItem(anom, false));
    }

    if (data.recent_events) {
      data.recent_events.forEach(ev => this.prependTickerRow(ev));
    }

    this.updateCounters();
  }

  handleAccessEvent(event) {
    this.stats.totalRequests++;
    this.stats.recentWindowReqs++;

    const sens = (event.sensitivity_level || 'INTERNAL').toUpperCase();
    this.stats.classifications[sens] = (this.stats.classifications[sens] || 0) + 1;
    if (this.charts) this.charts.updateClassification(this.stats.classifications);

    this.prependTickerRow(event);
    this.updateCounters();
  }

  handleAnomalyAlert(anomaly) {
    this.stats.totalAnomalies++;
    this.stats.recentWindowAnoms++;
    if (anomaly.severity === 'CRITICAL') this.stats.criticalAnomalies++;

    // 1. Add to Anomaly Feed with animation
    this.renderAnomalyItem(anomaly, true);

    // 2. Highlight on Canvas Graph
    if (this.graphVis) {
      this.graphVis.highlightAnomaly(anomaly.username, anomaly.resource_key, anomaly.severity);
    }

    // 3. Audio alert
    this.playAlertSound(anomaly.severity);

    // 4. Update counters
    this.updateCounters();
  }

  renderAnomalyItem(anomaly, isNew = false) {
    const feed = document.getElementById('anomalyFeed');
    if (!feed) return;

    const div = document.createElement('div');
    const sev = (anomaly.severity || 'MEDIUM').toLowerCase();
    div.className = `anomaly-item ${sev}`;
    div.dataset.anomalyJson = JSON.stringify(anomaly);

    const timeStr = anomaly.timestamp ? new Date(anomaly.timestamp).toLocaleTimeString() : 'Just now';

    div.innerHTML = `
      <div class="anomaly-top-row">
        <span class="severity-pill ${sev}">${anomaly.severity}</span>
        <span class="anomaly-time">${timeStr}</span>
      </div>
      <div class="anomaly-title">${this.getFriendlyAnomalyTitle(anomaly.anomaly_type)}</div>
      <div class="anomaly-explanation">${anomaly.explanation}</div>
      <div class="anomaly-meta-tags">
        <span class="tag">User: ${anomaly.username}</span>
        <span class="tag">Resource: ${anomaly.resource_key}</span>
        <span class="tag">Score: ${anomaly.score}</span>
        ${anomaly.is_resolved ? '<span class="tag" style="color:#10b981;">RESOLVED</span>' : ''}
      </div>
    `;

    div.addEventListener('click', () => this.openInvestigationModal(anomaly));

    if (isNew) {
      feed.insertBefore(div, feed.firstChild);
      // Remove oldest if > 35 items
      if (feed.children.length > 35) feed.removeChild(feed.lastChild);
    } else {
      feed.appendChild(div);
    }
  }

  getFriendlyAnomalyTitle(type) {
    switch (type) {
      case 'FREQUENCY_ZSCORE':
        return 'Data Access Velocity Burst (Z-Score Deviation)';
      case 'NOVEL_RESOURCE_ACCESS':
        return 'Graph Novelty: First-Time Privilege Access';
      case 'HIGH_FANOUT':
        return 'Graph Fan-Out: Horizontal Resource Reconnaissance';
      default:
        return type || 'Data Access Anomaly';
    }
  }

  prependTickerRow(event) {
    const tbody = document.getElementById('tickerBody');
    if (!tbody) return;

    const tr = document.createElement('tr');
    const timeStr = event.timestamp ? new Date(event.timestamp).toLocaleTimeString() : 'Now';
    const statusCls = event.status_code === 200 ? 's200' : (event.status_code === 429 ? 's429' : 's403');

    tr.innerHTML = `
      <td>${timeStr}</td>
      <td style="color:#38bdf8;">${event.username || 'unknown'}</td>
      <td><strong>${event.resource_key}</strong></td>
      <td><span class="tag">${event.sensitivity_level}</span></td>
      <td>${event.action || 'READ'}</td>
      <td><span class="badge-status ${statusCls}">${event.status_code || 200}</span></td>
    `;

    tbody.insertBefore(tr, tbody.firstChild);
    if (tbody.children.length > 25) {
      tbody.removeChild(tbody.lastChild);
    }
  }

  updateCounters() {
    const totalReqEl = document.getElementById('metricTotalRequests');
    const totalAnomEl = document.getElementById('metricTotalAnomalies');
    const criticalAnomEl = document.getElementById('metricCriticalAnomalies');
    const anomRateEl = document.getElementById('metricAnomalyRate');

    if (totalReqEl) totalReqEl.textContent = this.stats.totalRequests.toLocaleString();
    if (totalAnomEl) totalAnomEl.textContent = this.stats.totalAnomalies.toLocaleString();
    if (criticalAnomEl) criticalAnomEl.textContent = this.stats.criticalAnomalies.toLocaleString();

    if (anomRateEl) {
      const rate = this.stats.totalRequests > 0 
        ? ((this.stats.totalAnomalies / this.stats.totalRequests) * 100).toFixed(1)
        : '0.0';
      anomRateEl.textContent = `${rate}%`;
    }
  }

  playAlertSound(severity) {
    if (this.isMuted) return;
    try {
      const ctx = new (window.AudioContext || window.webkitAudioContext)();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = severity === 'CRITICAL' ? 'sawtooth' : 'sine';
      osc.frequency.setValueAtTime(severity === 'CRITICAL' ? 880 : 587, ctx.currentTime);
      gain.gain.setValueAtTime(0.08, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.35);

      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + 0.35);
    } catch (e) {
      // Browser audio restriction handling
    }
  }

  openInvestigationModal(anomaly) {
    const modal = document.getElementById('investigationModal');
    const body = document.getElementById('investigationBody');
    if (!modal || !body) return;

    let detailsHtml = '';
    if (anomaly.details_json) {
      try {
        const details = JSON.parse(anomaly.details_json);
        detailsHtml = `
          <div style="background: rgba(0,0,0,0.3); padding: 12px; border-radius: 6px; font-family: monospace; font-size: 0.8rem;">
            <pre>${JSON.stringify(details, null, 2)}</pre>
          </div>
        `;
      } catch (e) {
        detailsHtml = `<p>${anomaly.details_json}</p>`;
      }
    }

    body.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <span class="severity-pill ${(anomaly.severity||'MEDIUM').toLowerCase()}">${anomaly.severity}</span>
        <span style="font-family: monospace; color: #94a3b8;">ID: #${anomaly.id}</span>
      </div>
      <div>
        <h4 style="color:#fff; margin-bottom: 6px;">${this.getFriendlyAnomalyTitle(anomaly.anomaly_type)}</h4>
        <p style="color:#94a3b8; font-size:0.85rem;">${anomaly.explanation}</p>
      </div>
      <div style="display:grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size:0.8rem; background:rgba(255,255,255,0.03); padding:10px; border-radius:6px;">
        <div><strong>Actor:</strong> ${anomaly.username}</div>
        <div><strong>Resource:</strong> ${anomaly.resource_key}</div>
        <div><strong>Risk Score:</strong> ${anomaly.score}</div>
        <div><strong>Status:</strong> ${anomaly.is_resolved ? '<span style="color:#10b981;">Resolved</span>' : '<span style="color:#f43f5e;">Active Flag</span>'}</div>
      </div>
      <div>
        <h5 style="color:#cbd5e1; margin-bottom: 6px; font-size: 0.82rem;">Mathematical & Context Details:</h5>
        ${detailsHtml}
      </div>
    `;

    const resolveBtn = document.getElementById('resolveAnomalyBtn');
    if (resolveBtn) {
      resolveBtn.onclick = () => this.resolveAnomaly(anomaly.id);
      resolveBtn.style.display = anomaly.is_resolved ? 'none' : 'inline-flex';
    }

    modal.classList.add('active');
  }

  async resolveAnomaly(id) {
    try {
      const res = await fetch(`/api/v1/anomalies/${id}/resolve`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.currentUser.token}`,
        },
        body: JSON.stringify({ resolution_note: `Reviewed and resolved by ${this.currentUser.username}` }),
      });

      if (res.ok) {
        document.getElementById('investigationModal').classList.remove('active');
        // Refresh local feed
        const item = document.querySelector(`.anomaly-item[data-anomaly-json*='"id":${id}']`);
        if (item) {
          const tag = document.createElement('span');
          tag.className = 'tag';
          tag.style.color = '#10b981';
          tag.textContent = 'RESOLVED';
          item.querySelector('.anomaly-meta-tags').appendChild(tag);
        }
      }
    } catch (e) {
      console.error('Error resolving anomaly:', e);
    }
  }

  async openAuditLogModal() {
    const modal = document.getElementById('auditModal');
    const body = document.getElementById('auditBody');
    if (!modal || !body) return;

    if (this.currentUser.role !== 'admin') {
      alert('Access Denied: The Audit Log is strictly restricted to users with the Administrator role.');
      return;
    }

    modal.classList.add('active');
    body.innerHTML = '<p style="color:#94a3b8;">Querying immutable audit logs from database...</p>';

    try {
      const res = await fetch('/api/v1/audit-logs/?limit=100', {
        headers: { 'Authorization': `Bearer ${this.currentUser.token}` },
      });

      if (!res.ok) {
        body.innerHTML = `<p style="color:#f43f5e;">Forbidden (403): ${await res.text()}</p>`;
        return;
      }

      const logs = await res.json();
      if (!logs.length) {
        body.innerHTML = '<p style="color:#94a3b8;">No audit records found yet.</p>';
        return;
      }

      let html = `
        <table class="cyber-table">
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Actor</th>
              <th>Role</th>
              <th>Action</th>
              <th>Target Resource</th>
              <th>Classification</th>
              <th>Client IP</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
      `;

      logs.forEach(l => {
        html += `
          <tr>
            <td>${new Date(l.timestamp).toLocaleTimeString()}</td>
            <td style="color:#38bdf8;">${l.actor_username}</td>
            <td><span class="role-badge ${l.actor_role}">${l.actor_role}</span></td>
            <td>${l.action}</td>
            <td><strong>${l.target_resource}</strong></td>
            <td>${l.resource_classification}</td>
            <td>${l.client_ip}</td>
            <td><span class="badge-status ${l.response_status === 200 ? 's200' : 's403'}">${l.response_status}</span></td>
          </tr>
        `;
      });

      html += '</tbody></table>';
      body.innerHTML = html;
    } catch (e) {
      body.innerHTML = `<p style="color:#f43f5e;">Error loading audit logs: ${e}</p>`;
    }
  }

  async triggerAttack(scenario) {
    const btn = document.getElementById(`btnAttack_${scenario}`);
    if (btn) btn.disabled = true;

    try {
      const res = await fetch(`/api/v1/simulator/attack/${scenario}`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${this.currentUser.token}` },
      });
      const data = await res.json();
      console.log(`Triggered attack scenario '${scenario}':`, data);
    } catch (e) {
      console.error(`Failed to trigger attack '${scenario}':`, e);
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  async toggleSimulator(start) {
    const endpoint = start ? '/api/v1/simulator/start' : '/api/v1/simulator/stop';
    try {
      await fetch(endpoint, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${this.currentUser.token}` },
      });
      document.getElementById('btnSimStart').style.display = start ? 'none' : 'inline-flex';
      document.getElementById('btnSimPause').style.display = start ? 'inline-flex' : 'none';
    } catch (e) {
      console.error('Error toggling simulator:', e);
    }
  }

  async setSimulatorSpeed(multiplier, btnElement) {
    try {
      await fetch('/api/v1/simulator/speed', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.currentUser.token}`,
        },
        body: JSON.stringify({ multiplier }),
      });

      document.querySelectorAll('#speedGroup .btn').forEach(b => b.classList.remove('active'));
      if (btnElement) btnElement.classList.add('active');
    } catch (e) {
      console.error('Error setting simulator speed:', e);
    }
  }

  bindEvents() {
    // User Switcher
    const userSelect = document.getElementById('userSelect');
    if (userSelect) {
      userSelect.addEventListener('change', (e) => this.authenticate(e.target.value));
    }

    // Audio Mute Toggle
    const muteBtn = document.getElementById('muteToggle');
    if (muteBtn) {
      muteBtn.addEventListener('click', () => {
        this.isMuted = !this.isMuted;
        muteBtn.textContent = this.isMuted ? '🔇 Muted' : '🔊 Audio Alert';
        muteBtn.style.color = this.isMuted ? '#64748b' : '#38bdf8';
      });
    }

    // Visual Tabs (Graph vs Charts)
    const tabBtns = document.querySelectorAll('.tab-btn');
    tabBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        tabBtns.forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));

        btn.classList.add('active');
        const targetPane = document.getElementById(btn.dataset.target);
        if (targetPane) targetPane.classList.add('active');

        // Resize trigger for canvas or charts
        if (btn.dataset.target === 'paneGraph' && this.graphVis) this.graphVis.setupCanvas();
      });
    });

    // Attack Scenario Buttons
    const btnBurst = document.getElementById('btnAttack_exfiltration');
    if (btnBurst) btnBurst.addEventListener('click', () => this.triggerAttack('exfiltration'));

    const btnNovelty = document.getElementById('btnAttack_novelty');
    if (btnNovelty) btnNovelty.addEventListener('click', () => this.triggerAttack('novelty'));

    const btnFanout = document.getElementById('btnAttack_fanout');
    if (btnFanout) btnFanout.addEventListener('click', () => this.triggerAttack('fanout'));

    // Simulator Controls
    const btnSimStart = document.getElementById('btnSimStart');
    if (btnSimStart) btnSimStart.addEventListener('click', () => this.toggleSimulator(true));

    const btnSimPause = document.getElementById('btnSimPause');
    if (btnSimPause) btnSimPause.addEventListener('click', () => this.toggleSimulator(false));

    // Audit Log Modal Trigger
    const auditBtn = document.getElementById('btnOpenAudit');
    if (auditBtn) auditBtn.addEventListener('click', () => this.openAuditLogModal());

    // Modal Close buttons
    document.querySelectorAll('.close-modal').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.modal-overlay').forEach(m => m.classList.remove('active'));
      });
    });
  }
}

// Instantiate dashboard when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  window.sentinelDashboard = new SentinelDashboard();
});
