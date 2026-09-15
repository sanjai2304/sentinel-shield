/**
 * Chart.js Integration for SentinelShield SOC Dashboard.
 * Powers real-time access velocity & anomaly detection timelines.
 */

class DashboardCharts {
  constructor() {
    this.timelineChart = null;
    this.distributionChart = null;
    this.maxDataPoints = 18;

    this.timelineData = {
      labels: [],
      requests: [],
      anomalies: [],
    };

    this.initTimeline();
    this.initDistribution();
  }

  initTimeline() {
    const ctx = document.getElementById('timelineChart');
    if (!ctx) return;

    // Fill initial placeholder timestamps
    const now = new Date();
    for (let i = this.maxDataPoints; i >= 0; i--) {
      const t = new Date(now.getTime() - i * 5000);
      this.timelineData.labels.push(t.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
      this.timelineData.requests.push(0);
      this.timelineData.anomalies.push(0);
    }

    this.timelineChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: this.timelineData.labels,
        datasets: [
          {
            label: 'Access Requests',
            data: this.timelineData.requests,
            borderColor: '#38bdf8',
            backgroundColor: 'rgba(56, 189, 248, 0.1)',
            borderWidth: 2,
            tension: 0.35,
            fill: true,
            yAxisID: 'y',
          },
          {
            label: 'Flagged Anomalies',
            data: this.timelineData.anomalies,
            borderColor: '#f43f5e',
            backgroundColor: 'rgba(244, 63, 94, 0.25)',
            borderWidth: 2.5,
            pointBackgroundColor: '#f43f5e',
            pointRadius: 4,
            tension: 0.2,
            fill: false,
            yAxisID: 'y1',
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: {
            labels: { color: '#94a3b8', font: { family: 'Inter', size: 11 } },
          },
        },
        scales: {
          x: {
            grid: { color: 'rgba(255, 255, 255, 0.04)' },
            ticks: { color: '#64748b', font: { family: 'JetBrains Mono', size: 9 }, maxRotation: 0 },
          },
          y: {
            type: 'linear',
            position: 'left',
            beginAtZero: true,
            grid: { color: 'rgba(255, 255, 255, 0.04)' },
            ticks: { color: '#38bdf8', font: { family: 'JetBrains Mono', size: 10 } },
            title: { display: true, text: 'Req / 5s', color: '#64748b', font: { size: 10 } }
          },
          y1: {
            type: 'linear',
            position: 'right',
            beginAtZero: true,
            grid: { drawOnChartArea: false },
            ticks: { color: '#f43f5e', stepSize: 1, font: { family: 'JetBrains Mono', size: 10 } },
            title: { display: true, text: 'Anomalies', color: '#f43f5e', font: { size: 10 } }
          },
        },
      },
    });
  }

  initDistribution() {
    const ctx = document.getElementById('distributionChart');
    if (!ctx) return;

    this.distributionChart = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: ['Internal', 'Confidential', 'Restricted', 'Top Secret'],
        datasets: [{
          data: [12, 18, 8, 2],
          backgroundColor: ['#10b981', '#3b82f6', '#f59e0b', '#f43f5e'],
          borderWidth: 0,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'bottom',
            labels: { color: '#94a3b8', font: { family: 'Inter', size: 11 } },
          },
        },
        cutout: '68%',
      },
    });
  }

  pushDataPoint(reqCount, anomalyCount) {
    if (!this.timelineChart) return;

    const timeLabel = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    this.timelineData.labels.push(timeLabel);
    this.timelineData.requests.push(reqCount);
    this.timelineData.anomalies.push(anomalyCount);

    if (this.timelineData.labels.length > this.maxDataPoints) {
      this.timelineData.labels.shift();
      this.timelineData.requests.shift();
      this.timelineData.anomalies.shift();
    }

    this.timelineChart.update('none'); // Update without sluggish animations
  }

  updateClassification(counts) {
    if (!this.distributionChart || !counts) return;
    this.distributionChart.data.datasets[0].data = [
      counts.INTERNAL || 0,
      counts.CONFIDENTIAL || 0,
      counts.RESTRICTED || 0,
      counts.TOP_SECRET || 0,
    ];
    this.distributionChart.update();
  }
}

window.DashboardCharts = DashboardCharts;
