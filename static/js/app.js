/* global L */

const map = L.map("map", { attributionControl: false }).setView([59.93, 30.33], 11);

L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
  attribution: "",
}).addTo(map);

let segmentLayers = {};

function colorForCongestion(index) {
  if (index < 30) return "#16a34a"; // green
  if (index < 70) return "#facc15"; // yellow
  return "#dc2626"; // red
}

async function fetchJSON(url) {
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Request failed: ${res.status}`);
  }
  return res.json();
}

function parseGeometry(geometry) {
  try {
    const parsed = JSON.parse(geometry);
    if (parsed.type === "LineString") {
      return parsed.coordinates.map(([lng, lat]) => [lat, lng]);
    }
  } catch (e) {
    // Fallback: not a GeoJSON, ignore
  }
  return null;
}

async function loadTraffic() {
  try {
    const snapshots = await fetchJSON("/api/traffic/current");

    Object.values(segmentLayers).forEach((layer) => map.removeLayer(layer));
    segmentLayers = {};

    snapshots.forEach((snap) => {
      const coords = parseGeometry(snap.segment.geometry);
      if (!coords) return;

      const color = colorForCongestion(snap.congestion_index);
      const layer = L.polyline(coords, { color, weight: 6, opacity: 0.8 }).addTo(map);

      const speed = snap.latest_flow ? snap.latest_flow.average_speed.toFixed(1) : "—";
      const vehicles = snap.latest_flow ? snap.latest_flow.vehicle_count : "—";
      const alertBadge = snap.has_active_alert ? "<span class='text-red-600 font-semibold'>АЛЕРТ</span>" : "";

      layer.bindPopup(
        `<div class="text-sm">
          <div class="font-semibold mb-1">${snap.segment.name}</div>
          <div>Индекс загруженности: <span class="font-mono">${snap.congestion_index.toFixed(1)}</span></div>
          <div>Скорость: <span class="font-mono">${speed}</span> км/ч</div>
          <div>Транспортных средств: <span class="font-mono">${vehicles}</span></div>
          <div>${alertBadge}</div>
        </div>`
      );

      segmentLayers[snap.segment.id] = layer;
    });
  } catch (e) {
    // In prototype we simply log error
    console.error(e);
  }
}

async function loadAlerts() {
  const container = document.getElementById("alerts-list");
  container.innerHTML = "";
  try {
    const alerts = await fetchJSON("/api/alerts/?only_active=true");
    if (!alerts.length) {
      container.innerHTML = '<li class="text-gray-500">Нет активных алертов</li>';
      return;
    }
    alerts.forEach((a) => {
      const li = document.createElement("li");
      li.innerHTML = `<span class="font-semibold">#${a.id}</span> · ${a.type} · 
        <span class="text-red-600">sev=${a.severity}</span> · ${a.description || ""}`;
      container.appendChild(li);
    });
  } catch (e) {
    console.error(e);
    container.innerHTML = '<li class="text-red-600">Ошибка загрузки алертов</li>';
  }
}

async function loadMetrics() {
  const container = document.getElementById("metrics-list");
  container.innerHTML = "";
  try {
    const metrics = await fetchJSON("/api/metrics/summary?limit=5");
    if (!metrics.length) {
      container.innerHTML = '<li class="text-gray-500">Метрики пока не рассчитаны</li>';
      return;
    }
    metrics.forEach((m) => {
      const li = document.createElement("li");
      li.innerHTML = `Сегмент ${m.segment_id}: индекс=${m.congestion_index.toFixed(
        1
      )}, средний поток=${m.average_flow.toFixed(1)}`;
      container.appendChild(li);
    });
  } catch (e) {
    console.error(e);
    container.innerHTML = '<li class="text-red-600">Ошибка загрузки метрик</li>';
  }
}

async function refreshAll() {
  await Promise.all([loadTraffic(), loadAlerts(), loadMetrics()]);
}

document.getElementById("refresh-btn").addEventListener("click", () => {
  refreshAll();
});

refreshAll();
setInterval(refreshAll, 15000);

