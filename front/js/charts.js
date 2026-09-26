/**
 * VISUALIZACIÓN DINÁMICA DE LLUVIAS Y BALANCE HÍDRICO (RF-04)
 * Curvas fenológicas de 60 días para maíz en Jutiapa con Chart.js
 * Diseño moderno, limpio y claro (Cropler Light Theme)
 */

class WaterBalanceChart {
  constructor(canvasId) {
    this.canvasId = canvasId;
    this.chart = null;
  }

  update(timelineData) {
    const ctx = document.getElementById(this.canvasId);
    if (!ctx) return;

    if (this.chart) {
      this.chart.destroy();
    }

    const labels = timelineData.days.map(d => `D${d}`);

    this.chart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [
          {
            type: 'bar',
            label: 'Lluvia Diaria (mm)',
            data: timelineData.precipDaily,
            backgroundColor: 'rgba(56, 189, 248, 0.45)',
            borderColor: '#0284C7',
            borderWidth: 1,
            borderRadius: 3,
            yAxisID: 'yDaily',
            order: 3
          },
          {
            type: 'line',
            label: 'Lluvia Acumulada (mm)',
            data: timelineData.precipAcc,
            borderColor: '#0369A1',
            backgroundColor: 'rgba(3, 105, 161, 0.05)',
            borderWidth: 2.2,
            tension: 0.25,
            pointRadius: 0,
            yAxisID: 'yAcc',
            order: 1
          },
          {
            type: 'line',
            label: 'Demanda Hídrica ETc Acum. (mm)',
            data: timelineData.etcAcc,
            borderColor: '#DC2626',
            borderWidth: 2,
            borderDash: [5, 4],
            tension: 0.25,
            pointRadius: 0,
            yAxisID: 'yAcc',
            order: 2
          },
          {
            type: 'line',
            label: 'Humedad Útil Suelo (%)',
            data: timelineData.soilFrac.map(v => Math.round(v * 100)),
            borderColor: '#16A34A',
            borderWidth: 2.2,
            tension: 0.3,
            pointRadius: 0,
            yAxisID: 'ySoil',
            order: 0
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false
        },
        plugins: {
          legend: {
            position: 'top',
            labels: {
              color: '#475569',
              font: { family: 'Inter', size: 12, weight: '500' },
              boxWidth: 12,
              usePointStyle: true,
              padding: 16
            }
          },
          tooltip: {
            backgroundColor: '#FFFFFF',
            titleColor: '#0F172A',
            bodyColor: '#334155',
            borderColor: '#E2E8F0',
            borderWidth: 1,
            padding: 12,
            boxPadding: 6,
            usePointStyle: true,
            boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
            callbacks: {
              label: function(context) {
                let label = context.dataset.label || '';
                let val = context.parsed.y;
                if (label.includes('%')) return `${label}: ${val}%`;
                return `${label}: ${val.toFixed(1)} mm`;
              }
            }
          }
        },
        scales: {
          x: {
            grid: { color: '#F1F5F9' },
            ticks: {
              color: '#64748B',
              font: { family: 'JetBrains Mono', size: 10.5 },
              maxTicksLimit: 12
            }
          },
          yDaily: {
            type: 'linear',
            position: 'left',
            grid: { color: '#F1F5F9' },
            title: {
              display: true,
              text: 'Lluvia Diaria (mm)',
              color: '#0284C7',
              font: { family: 'Inter', size: 11, weight: '600' }
            },
            ticks: { color: '#64748B' },
            suggestedMax: 30
          },
          yAcc: {
            type: 'linear',
            position: 'right',
            grid: { drawOnChartArea: false },
            title: {
              display: true,
              text: 'Acumulado (mm)',
              color: '#0369A1',
              font: { family: 'Inter', size: 11, weight: '600' }
            },
            ticks: { color: '#64748B' }
          },
          ySoil: {
            type: 'linear',
            position: 'right',
            grid: { drawOnChartArea: false },
            min: 0,
            max: 100,
            title: {
              display: true,
              text: 'Humedad Suelo (%)',
              color: '#16A34A',
              font: { family: 'Inter', size: 11, weight: '600' }
            },
            ticks: { color: '#16A34A' }
          }
        }
      }
    });
  }
}

window.WaterBalanceChart = WaterBalanceChart;
