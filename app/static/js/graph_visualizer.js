/**
 * HTML5 Canvas Bipartite Graph Visualizer for SentinelShield.
 * Renders User <-> Resource access topology with real-time glowing anomaly edges.
 */

class BipartiteGraphVisualizer {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    if (!this.canvas) return;
    this.ctx = this.canvas.getContext('2d');
    
    this.nodes = new Map(); // id -> node object
    this.edges = [];        // list of edge objects
    this.anomalyEdges = []; // recent anomalous connections: [{source, target, time, severity}]

    this.width = this.canvas.clientWidth;
    this.height = this.canvas.clientHeight;
    this.devicePixelRatio = window.devicePixelRatio || 1;

    this.setupCanvas();
    this.bindEvents();
    this.startAnimationLoop();
  }

  setupCanvas() {
    const rect = this.canvas.getBoundingClientRect();
    this.width = rect.width;
    this.height = rect.height;
    this.canvas.width = this.width * this.devicePixelRatio;
    this.canvas.height = this.height * this.devicePixelRatio;
    this.ctx.scale(this.devicePixelRatio, this.devicePixelRatio);
  }

  bindEvents() {
    window.addEventListener('resize', () => this.setupCanvas());
  }

  updateTopology(topologyData) {
    if (!topologyData) return;

    const rawNodes = topologyData.nodes || [];
    const rawEdges = topologyData.edges || [];

    // Separate users and resources for bipartite layout
    const users = [];
    const resources = [];

    rawNodes.forEach(n => {
      if (n.type === 'user' || n.id.startsWith('user:')) {
        users.push(n);
      } else {
        resources.push(n);
      }
    });

    const cx = this.width / 2;
    const cy = this.height / 2;

    // Arrange Users on an inner circle or left column
    users.forEach((u, i) => {
      const angle = (i / Math.max(users.length, 1)) * Math.PI * 2 - Math.PI / 2;
      const radius = Math.min(this.width, this.height) * 0.22;
      const x = cx + radius * Math.cos(angle);
      const y = cy + radius * Math.sin(angle);

      this.nodes.set(u.id, {
        id: u.id,
        label: u.label || u.id.replace('user:', ''),
        type: 'user',
        x, y,
        targetX: x,
        targetY: y,
        radius: 16,
        color: '#38bdf8',
      });
    });

    // Arrange Resources on an outer ring
    resources.forEach((r, i) => {
      const angle = (i / Math.max(resources.length, 1)) * Math.PI * 2 - Math.PI / 2;
      const radius = Math.min(this.width, this.height) * 0.40;
      const x = cx + radius * Math.cos(angle);
      const y = cy + radius * Math.sin(angle);

      let color = '#10b981'; // default INTERNAL
      const sens = (r.sensitivity || '').toUpperCase();
      if (sens === 'TOP_SECRET') color = '#f43f5e';
      else if (sens === 'RESTRICTED') color = '#f59e0b';
      else if (sens === 'CONFIDENTIAL') color = '#3b82f6';

      this.nodes.set(r.id, {
        id: r.id,
        label: r.label || r.id.replace('res:', ''),
        type: 'resource',
        sensitivity: sens,
        x, y,
        targetX: x,
        targetY: y,
        radius: 12,
        color,
      });
    });

    this.edges = rawEdges;
  }

  highlightAnomaly(userId, resourceKey, severity = 'CRITICAL') {
    const userNodeId = userId.startsWith('user:') ? userId : `user:${userId}`;
    const resNodeId = resourceKey.startsWith('res:') ? resourceKey : `res:${resourceKey}`;

    // Ensure dummy nodes exist if not yet in topology
    if (!this.nodes.has(userNodeId)) {
      this.nodes.set(userNodeId, {
        id: userNodeId,
        label: userId.replace('user:', ''),
        type: 'user',
        x: this.width * 0.35,
        y: this.height * 0.5,
        radius: 16,
        color: '#38bdf8',
      });
    }

    if (!this.nodes.has(resNodeId)) {
      this.nodes.set(resNodeId, {
        id: resNodeId,
        label: resourceKey.replace('res:', ''),
        type: 'resource',
        x: this.width * 0.65,
        y: this.height * 0.5,
        radius: 14,
        color: '#f43f5e',
      });
    }

    this.anomalyEdges.push({
      source: userNodeId,
      target: resNodeId,
      severity,
      created: Date.now(),
      lifetime: 8000, // glow for 8 seconds
    });
  }

  startAnimationLoop() {
    const render = () => {
      this.draw();
      requestAnimationFrame(render);
    };
    requestAnimationFrame(render);
  }

  draw() {
    if (!this.ctx) return;
    const now = Date.now();
    this.ctx.clearRect(0, 0, this.width, this.height);

    // Filter expired anomaly edges
    this.anomalyEdges = this.anomalyEdges.filter(e => now - e.created < e.lifetime);

    // 1. Draw Normal Edges
    this.edges.forEach(e => {
      const source = this.nodes.get(e.source);
      const target = this.nodes.get(e.target);
      if (!source || !target) return;

      this.ctx.beginPath();
      this.ctx.moveTo(source.x, source.y);
      this.ctx.lineTo(target.x, target.y);
      this.ctx.strokeStyle = 'rgba(255, 255, 255, 0.08)';
      this.ctx.lineWidth = Math.min(1 + (e.weight || 1) * 0.3, 3);
      this.ctx.stroke();
    });

    // 2. Draw Pulsing Anomaly Edges
    this.anomalyEdges.forEach(ae => {
      const source = this.nodes.get(ae.source);
      const target = this.nodes.get(ae.target);
      if (!source || !target) return;

      const progress = (now - ae.created) / ae.lifetime;
      const alpha = Math.max(0, 1 - progress);
      const pulse = Math.sin(now * 0.008) * 0.5 + 0.5;

      this.ctx.save();
      this.ctx.beginPath();
      this.ctx.moveTo(source.x, source.y);
      this.ctx.lineTo(target.x, target.y);
      this.ctx.strokeStyle = `rgba(244, 63, 94, ${alpha})`;
      this.ctx.lineWidth = 3 + pulse * 3;
      this.ctx.shadowColor = '#f43f5e';
      this.ctx.shadowBlur = 15;
      this.ctx.stroke();
      this.ctx.restore();
    });

    // 3. Draw Nodes
    this.nodes.forEach(node => {
      this.ctx.save();

      // Node body circle
      this.ctx.beginPath();
      this.ctx.arc(node.x, node.y, node.radius, 0, Math.PI * 2);
      this.ctx.fillStyle = node.color;
      this.ctx.shadowColor = node.color;
      this.ctx.shadowBlur = 10;
      this.ctx.fill();

      // Node border
      this.ctx.lineWidth = 2;
      this.ctx.strokeStyle = '#ffffff';
      this.ctx.stroke();

      // Node label
      this.ctx.shadowBlur = 0;
      this.ctx.font = node.type === 'user' ? '600 11px Inter, sans-serif' : '500 10px JetBrains Mono, monospace';
      this.ctx.fillStyle = '#ffffff';
      this.ctx.textAlign = 'center';
      this.ctx.textBaseline = 'middle';

      const labelText = node.label.length > 14 ? node.label.substring(0, 12) + '..' : node.label;
      const textY = node.type === 'user' ? node.y + node.radius + 12 : node.y - node.radius - 8;
      
      // Label backdrop pill
      const textWidth = this.ctx.measureText(labelText).width;
      this.ctx.fillStyle = 'rgba(15, 21, 35, 0.75)';
      this.ctx.fillRect(node.x - textWidth / 2 - 4, textY - 6, textWidth + 8, 13);

      this.ctx.fillStyle = node.type === 'user' ? '#7dd3fc' : '#e2e8f0';
      this.ctx.fillText(labelText, node.x, textY);

      this.ctx.restore();
    });
  }
}

window.BipartiteGraphVisualizer = BipartiteGraphVisualizer;
