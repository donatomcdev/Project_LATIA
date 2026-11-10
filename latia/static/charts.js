"use strict";

const source = document.querySelector("#chart-data");
const trendCharts = document.querySelector("#trend-charts");
const canvases = document.querySelectorAll(".chart canvas");
const data = JSON.parse(source.textContent);

function renderTrends(colors) {
  const first = data[0].timestamp;
  const last = data[data.length - 1].timestamp;
  const span = last - first;
  const padding = span ? span * 0.025 : 30 * 60 * 1000;
  const timeZone = trendCharts.dataset.timezone;
  const day = 24 * 60 * 60 * 1000;
  const dateFormat = new Intl.DateTimeFormat("es", {
    timeZone,
    day: "numeric",
    month: "short",
    ...(span >= 365 * day ? { year: "numeric" } : {})
  });
  const timeFormat = new Intl.DateTimeFormat("es", { timeZone, hour: "2-digit", minute: "2-digit", hourCycle: "h23" });
  const timestamps = [...new Set(data.map(row => row.timestamp))];
  const tickCount = Math.min(6, timestamps.length);
  const ticks = Array.from({ length: tickCount }, (_, index) =>
    timestamps[Math.round(index * (timestamps.length - 1) / Math.max(1, tickCount - 1))]);

  renderTrend(document.querySelector("#pressure-chart"), "mmHg", [
    ["systolic", "Sistólica", colors[0]],
    ["diastolic", "Diastólica", colors[1]]
  ]);
  renderTrend(document.querySelector("#pulse-chart"), "lpm", [["pulse", "Pulso", colors[2]]]);

  function renderTrend(canvas, unit, metrics) {
    new Chart(canvas, {
      type: "line",
      data: {
        datasets: metrics.map(([key, label, color]) => ({
          label,
          data: data.map(row => ({ x: row.timestamp, y: row[key], date: row.label })),
          borderColor: color,
          backgroundColor: color,
          pointRadius: data.length > 60 ? 0 : 3,
          pointHitRadius: 12
        }))
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        interaction: { mode: "index", intersect: false },
        plugins: {
          tooltip: {
            callbacks: {
              title: items => items[0].raw.date,
              label: item => `${item.dataset.label}: ${item.parsed.y} ${unit}`
            }
          }
        },
        scales: {
          x: {
            type: "linear",
            min: first - padding,
            max: last + padding,
            afterBuildTicks: axis => { axis.ticks = ticks.map(value => ({ value })); },
            ticks: {
              autoSkip: true,
              maxRotation: 0,
              callback: value => span < 6 * day
                ? [dateFormat.format(value), timeFormat.format(value)]
                : dateFormat.format(value)
            }
          },
          y: {
            beginAtZero: true,
            title: { display: true, text: unit },
            afterFit: axis => { axis.width = 62; }
          }
        }
      }
    });
  }
}

function renderStats(colors) {
  new Chart(canvases[0], {
    type: "bar",
    data: {
      labels: data.map(([label, unit]) => `${label} (${unit})`),
      datasets: [
        { label: "Mínimo", data: data.map(row => row[3]), backgroundColor: "#83a394" },
        { label: "Promedio", data: data.map(row => Number(row[2].replace(",", "."))), backgroundColor: colors[0] },
        { label: "Máximo", data: data.map(row => row[4]), backgroundColor: colors[1] }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      scales: { y: { beginAtZero: true } }
    }
  });
}

function renderChart() {
  const theme = getComputedStyle(document.documentElement);
  const colors = ["green", "blue", "orange"].map(color => theme.getPropertyValue(`--chart-${color}`).trim());
  Chart.defaults.color = theme.getPropertyValue("--muted").trim();
  Chart.defaults.borderColor = theme.getPropertyValue("--border").trim();
  canvases.forEach(canvas => Chart.getChart(canvas)?.destroy());
  if (trendCharts) {
    renderTrends(colors);
  } else {
    renderStats(colors);
  }
}

if (typeof Chart === "undefined") {
  (trendCharts || canvases[0].parentElement).hidden = true;
  document.querySelector("#chart-error").hidden = false;
} else {
  renderChart();
  document.addEventListener("latia-theme-change", renderChart);
}
