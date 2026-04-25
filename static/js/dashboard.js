/* ═══════════════════════════════════════════════════════════════
   DASHBOARD.JS — Charts, interactions, delete logic
═══════════════════════════════════════════════════════════════ */

'use strict';

/* ── Read chart data injected by Flask ────────────────────────── */
var CHART_DATA = (function () {
  var el = document.getElementById('chartData');
  try { return el ? JSON.parse(el.textContent) : {}; } catch (e) { return {}; }
})();

/* ── Chart.js global defaults (dark theme) ──────────────────── */
Chart.defaults.color          = '#8892b0';
Chart.defaults.borderColor    = '#1e2840';
Chart.defaults.font.family    = "'IBM Plex Sans', sans-serif";
Chart.defaults.font.size      = 12;

/* ── Shared gradient helper ──────────────────────────────────── */
function createLinearGradient(ctx, colorTop, colorBottom) {
  var grad = ctx.createLinearGradient(0, 0, 0, ctx.canvas.clientHeight || 240);
  grad.addColorStop(0, colorTop);
  grad.addColorStop(1, colorBottom);
  return grad;
}

/* ══════════════════════════════════════════════════════════════
   1. MONTHLY BAR CHART
══════════════════════════════════════════════════════════════ */
(function initMonthlyChart() {
  var canvas = document.getElementById('monthlyChart');
  if (!canvas) return;

  var monthly = CHART_DATA.monthly || { labels: [], values: [] };

  var ctx = canvas.getContext('2d');
  var grad = createLinearGradient(ctx, 'rgba(124,92,252,0.8)', 'rgba(124,92,252,0.15)');

  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: monthly.labels,
      datasets: [{
        label: 'Total Spent (₹)',
        data: monthly.values,
        backgroundColor: monthly.values.map(function(v, i) {
          return i === monthly.values.length - 1
            ? 'rgba(124,92,252,0.9)'
            : 'rgba(124,92,252,0.4)';
        }),
        borderColor: monthly.values.map(function(v, i) {
          return i === monthly.values.length - 1
            ? 'rgba(155,127,254,1)'
            : 'rgba(124,92,252,0.6)';
        }),
        borderWidth: 1.5,
        borderRadius: 6,
        borderSkipped: false,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#161b28',
          borderColor: '#2a3550',
          borderWidth: 1,
          titleColor: '#eef2ff',
          bodyColor: '#9b7ffe',
          padding: 12,
          callbacks: {
            label: function(ctx) {
              return '  ₹' + ctx.parsed.y.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
            }
          }
        }
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: '#4a5568', font: { size: 11 } },
        },
        y: {
          grid: { color: 'rgba(30, 40, 64, 0.8)', drawBorder: false },
          ticks: {
            color: '#4a5568',
            font: { size: 11 },
            callback: function(val) { return '₹' + val.toLocaleString(); }
          },
          border: { display: false }
        }
      },
      animation: {
        duration: 700,
        easing: 'easeOutQuart',
        delay: function(ctx) { return ctx.dataIndex * 60; }
      }
    }
  });
})();


/* ══════════════════════════════════════════════════════════════
   2. PIE CHART (Category breakdown)
══════════════════════════════════════════════════════════════ */
(function initPieChart() {
  var canvas = document.getElementById('pieChart');
  if (!canvas) return;

  var pie = CHART_DATA.pie || { labels: [], values: [], colors: [] };
  if (!pie.labels.length) return;

  var ctx = canvas.getContext('2d');
  var legendEl = document.getElementById('pieLegend');

  new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: pie.labels,
      datasets: [{
        data: pie.values,
        backgroundColor: pie.colors.map(function(c) { return hexToRgba(c, 0.85); }),
        borderColor: pie.colors.map(function(c) { return hexToRgba(c, 1); }),
        borderWidth: 1.5,
        hoverOffset: 6,
        hoverBorderWidth: 2,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '68%',
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#161b28',
          borderColor: '#2a3550',
          borderWidth: 1,
          titleColor: '#eef2ff',
          bodyColor: '#8892b0',
          padding: 12,
          callbacks: {
            label: function(ctx) {
              var total = ctx.dataset.data.reduce(function(a, b) { return a + b; }, 0);
              var pct = total > 0 ? ((ctx.parsed / total) * 100).toFixed(1) : 0;
              return '  ₹' + ctx.parsed.toLocaleString('en-US', {minimumFractionDigits: 2}) + ' (' + pct + '%)';
            }
          }
        }
      },
      animation: { animateRotate: true, duration: 700, easing: 'easeOutQuart' }
    }
  });

  // Build custom legend
  if (legendEl) {
    var total = pie.values.reduce(function(a, b) { return a + b; }, 0);
    legendEl.innerHTML = pie.labels.map(function(label, i) {
      var pct = total > 0 ? ((pie.values[i] / total) * 100).toFixed(0) : 0;
      return '<div class="legend-item">' +
             '<div class="legend-dot" style="background:' + pie.colors[i] + '"></div>' +
             '<span>' + label + ' <span style="color:#4a5568">(' + pct + '%)</span></span>' +
             '</div>';
    }).join('');
  }
})();


/* ══════════════════════════════════════════════════════════════
   3. WEEKLY BAR CHART
══════════════════════════════════════════════════════════════ */
(function initWeeklyChart() {
  var canvas = document.getElementById('weeklyChart');
  if (!canvas) return;

  var weekly = CHART_DATA.weekly || { labels: [], values: [] };

  var ctx = canvas.getContext('2d');
  var maxVal = Math.max.apply(null, weekly.values);

  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: weekly.labels,
      datasets: [{
        label: 'Weekly Spending (₹)',
        data: weekly.values,
        backgroundColor: weekly.values.map(function(v) {
          var intensity = maxVal > 0 ? (v / maxVal) : 0;
          return 'rgba(56,189,248,' + (0.3 + intensity * 0.6) + ')';
        }),
        borderColor: 'rgba(56,189,248,0.8)',
        borderWidth: 1.5,
        borderRadius: 6,
        borderSkipped: false,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#161b28',
          borderColor: '#2a3550',
          borderWidth: 1,
          titleColor: '#eef2ff',
          bodyColor: '#38bdf8',
          padding: 12,
          callbacks: {
            label: function(ctx) {
              return '  ₹' + ctx.parsed.y.toLocaleString('en-US', {minimumFractionDigits: 2});
            }
          }
        }
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: '#4a5568', font: { size: 11 } }
        },
        y: {
          grid: { color: 'rgba(30,40,64,0.8)', drawBorder: false },
          ticks: {
            color: '#4a5568',
            font: { size: 11 },
            callback: function(val) { return '₹' + val; }
          },
          border: { display: false }
        }
      },
      animation: {
        duration: 600,
        easing: 'easeOutQuart',
        delay: function(ctx) { return ctx.dataIndex * 80; }
      }
    }
  });
})();


/* ══════════════════════════════════════════════════════════════
   4. DELETE EXPENSE
══════════════════════════════════════════════════════════════ */
function deleteExpense(expenseId, btn) {
  if (!confirm('Delete this expense? This cannot be undone.')) return;

  btn.disabled = true;
  btn.style.opacity = '0.5';

  fetch('/expenses/' + expenseId, {
    method: 'DELETE',
    headers: { 'X-Requested-With': 'XMLHttpRequest' }
  })
  .then(function(res) { return res.json(); })
  .then(function(data) {
    if (data.success) {
      var item = btn.closest('.transaction-item');
      item.style.transition = 'all 0.3s ease';
      item.style.opacity = '0';
      item.style.transform = 'translateX(20px)';
      setTimeout(function() {
        item.remove();
        // Check if list is now empty
        var list = document.getElementById('transactionsList');
        if (list && !list.querySelector('.transaction-item')) {
          list.innerHTML = '<div class="empty-state"><p>No recent transactions</p></div>';
        }
      }, 300);
    } else {
      alert('Could not delete expense. Please try again.');
      btn.disabled = false;
      btn.style.opacity = '1';
    }
  })
  .catch(function() {
    alert('Network error. Please try again.');
    btn.disabled = false;
    btn.style.opacity = '1';
  });
}


/* ══════════════════════════════════════════════════════════════
   5. CHATBOT TOGGLE
══════════════════════════════════════════════════════════════ */



/* ══════════════════════════════════════════════════════════════
   UTILITIES
══════════════════════════════════════════════════════════════ */
function hexToRgba(hex, alpha) {
  alpha = alpha !== undefined ? alpha : 1;
  var r = parseInt(hex.slice(1, 3), 16);
  var g = parseInt(hex.slice(3, 5), 16);
  var b = parseInt(hex.slice(5, 7), 16);
  return 'rgba(' + r + ',' + g + ',' + b + ',' + alpha + ')';
}

/* Format timestamp as "HH:MM" */
function nowTime() {
  var d = new Date();
  return d.getHours().toString().padStart(2,'0') + ':' + d.getMinutes().toString().padStart(2,'0');
}

/* --------------------------------------------------------------
   6. EVENT LISTENERS
 -------------------------------------------------------------- */
document.addEventListener('DOMContentLoaded', function() {
  // Handle transaction delete buttons
  document.querySelectorAll('.txn-delete').forEach(function(btn) {
    btn.addEventListener('click', function() {
      var id = this.getAttribute('data-id');
      if (id) deleteExpense(id, this);
    });
  });
});
