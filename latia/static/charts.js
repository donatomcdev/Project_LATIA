"use strict";

const source = document.querySelector("#chart-data");
const canvas = document.querySelector(".chart canvas");
const data = JSON.parse(source.textContent);
const colors = ["#145a3b", "#236388", "#a64a00"];

function renderTrends() {
  const dateFormat = new Intl.DateTimeFormat("es", {
    timeZone: canvas.dataset.timezone,
    day: "numeric",
    month: "short"
  });
  const metrics = [
    { key: "systolic", label: "Sistólica", unit: "mmHg" },
    { key: "diastolic", label: "Diastólica", unit: "mmHg" },
    { key: "pulse", label: "Pulso", unit: "lpm" }
  ];
  new Chart(canvas, {
    type: "line",
    data: {
      datasets: metrics.map(({ key, label, unit }, index) => ({
        label,
        unit,
        data: data.map(row => ({ x: row.timestamp, y: row[key], date: row.label })),
        borderColor: colors[index],
        backgroundColor: colors[index],
        pointRadius: data.length > 60 ? 0 : 3,
        pointHitRadius: 12,
        yAxisID: key === "pulse" ? "pulse" : "pressure"
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
            label: item => `${item.dataset.label}: ${item.parsed.y} ${item.dataset.unit}`
          }
        }
      },
      scales: {
        x: { type: "linear", ticks: { maxTicksLimit: 6, callback: value => dateFormat.format(value) } },
        pressure: { title: { display: true, text: "mmHg" } },
        pulse: { position: "right", title: { display: true, text: "lpm" }, grid: { drawOnChartArea: false } }
      }
    }
  });
}

function renderStats() {
  new Chart(canvas, {
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

if (typeof Chart === "undefined") {
  canvas.parentElement.hidden = true;
  document.querySelector("#chart-error").hidden = false;
} else if (canvas.id === "trend-chart") {
  renderTrends();
} else {
  renderStats();
}
