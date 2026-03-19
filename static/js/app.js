/* global L */

const hasLeaflet = typeof window !== "undefined" && typeof window.L !== "undefined";
let map = null;

function showMapFallback(message) {
  const el = document.getElementById("map");
  if (!el) return;
  el.innerHTML = `
    <div class="h-full w-full flex items-center justify-center p-6">
      <div class="max-w-md rounded-2xl bg-white/5 p-5 text-center ring-1 ring-white/10">
        <div class="text-sm font-semibold text-white">Карта недоступна</div>
        <div class="mt-2 text-xs text-slate-300">${message}</div>
        <div class="mt-3 text-[11px] text-slate-400">KPI/алерты/метрики продолжат обновляться.</div>
      </div>
    </div>
  `;
}

if (hasLeaflet) {
  map = L.map("map", { attributionControl: false }).setView([59.93, 30.33], 11);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "",
  }).addTo(map);
} else {
  showMapFallback(
    "Не удалось загрузить Leaflet (CDN). Сделай hard refresh или проверь доступ к `unpkg.com`."
  );
}

let segmentLayers = {};
let latestSnapshots = [];

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

function formatTimeHHMM(date) {
  const pad = (n) => String(n).padStart(2, "0");
  return `${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}

function setSelected(snapshot) {
  if (!snapshot) {
    setText("selected-speed", "—");
    setText("selected-vehicles", "—");
    setText("selected-index", "—");
    const badge = document.getElementById("selected-badge");
    if (badge) badge.classList.add("hidden");
    return;
  }

  const speed = snapshot.latest_flow ? snapshot.latest_flow.average_speed.toFixed(1) : "—";
  const vehicles = snapshot.latest_flow ? String(snapshot.latest_flow.vehicle_count) : "—";
  const idx = snapshot.congestion_index.toFixed(1);
  setText("selected-speed", `${speed} км/ч`);
  setText("selected-vehicles", vehicles);
  setText("selected-index", idx);

  const badge = document.getElementById("selected-badge");
  if (badge) {
    badge.classList.remove("hidden");
    badge.textContent = snapshot.segment.name;
  }
}

async function loadTraffic() {
  try {
    const snapshots = await fetchJSON("/api/traffic/current");
    latestSnapshots = snapshots;

    if (map) {
      Object.values(segmentLayers).forEach((layer) => map.removeLayer(layer));
      segmentLayers = {};
    }

    setText("kpi-segments", String(snapshots.length));
    const congested = snapshots.filter((s) => s.congestion_index >= 70).length;
    setText("kpi-congested", String(congested));
    setText("kpi-updated", formatTimeHHMM(new Date()));

    // If Leaflet failed to load, we still update KPIs and lists (no map rendering).
    if (!map) return;

    snapshots.forEach((snap) => {
      const coords = parseGeometry(snap.segment.geometry);
      if (!coords) return;

      const color = colorForCongestion(snap.congestion_index);
      const layer = L.polyline(coords, { color, weight: 6, opacity: 0.9, lineJoin: "round" }).addTo(map);

      const speed = snap.latest_flow ? snap.latest_flow.average_speed.toFixed(1) : "—";
      const vehicles = snap.latest_flow ? snap.latest_flow.vehicle_count : "—";
      const alertBadge = snap.has_active_alert
        ? "<span class='inline-flex items-center rounded-full bg-rose-500/15 px-2 py-0.5 text-xs font-semibold text-rose-200 ring-1 ring-rose-500/30'>АЛЕРТ</span>"
        : "";

      layer.bindPopup(
        `<div class="text-sm">
          <div class="font-semibold mb-2 text-slate-100">${snap.segment.name}</div>
          <div class="grid grid-cols-2 gap-2">
            <div class="rounded-lg bg-slate-950/60 p-2 ring-1 ring-white/10">
              <div class="text-[11px] text-slate-300">Индекс</div>
              <div class="font-mono text-slate-50">${snap.congestion_index.toFixed(1)}</div>
            </div>
            <div class="rounded-lg bg-slate-950/60 p-2 ring-1 ring-white/10">
              <div class="text-[11px] text-slate-300">Скорость</div>
              <div class="font-mono text-slate-50">${speed} км/ч</div>
            </div>
            <div class="rounded-lg bg-slate-950/60 p-2 ring-1 ring-white/10 col-span-2">
              <div class="text-[11px] text-slate-300">Транспорт</div>
              <div class="font-mono text-slate-50">${vehicles}</div>
            </div>
          </div>
          <div class="mt-2">${alertBadge}</div>
        </div>`
      );

      layer.on("click", () => setSelected(snap));
      segmentLayers[snap.segment.id] = layer;
    });
  } catch (e) {
    // In prototype we simply log error
    console.error(e);
  }
}

function alertTypeBadge(type) {
  const base =
    "inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-semibold ring-1";
  if (type === "ACCIDENT") return `${base} bg-orange-500/15 text-orange-200 ring-orange-500/30`;
  if (type === "HAZARD") return `${base} bg-violet-500/15 text-violet-200 ring-violet-500/30`;
  return `${base} bg-rose-500/15 text-rose-200 ring-rose-500/30`; // CONGESTION
}

async function resolveAlert(id) {
  const res = await fetch(`/api/alerts/${id}/resolve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ resolved: true }),
  });
  if (!res.ok) throw new Error(`Resolve failed: ${res.status}`);
}

async function loadAlerts() {
  const container = document.getElementById("alerts-list");
  container.innerHTML = "";
  try {
    const alerts = await fetchJSON("/api/alerts/?only_active=true");
    setText("kpi-alerts", String(alerts.length));
    setText("alerts-count-pill", String(alerts.length));
    if (!alerts.length) {
      container.innerHTML =
        '<li class="rounded-xl bg-slate-950/50 p-3 text-slate-300 ring-1 ring-white/10">Нет активных алертов</li>';
      return;
    }
    alerts.forEach((a) => {
      const li = document.createElement("li");
      li.className = "rounded-xl bg-slate-950/50 p-3 ring-1 ring-white/10";
      li.innerHTML = `
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0">
            <div class="flex flex-wrap items-center gap-2">
              <span class="text-xs font-semibold text-slate-200">#${a.id}</span>
              <span class="${alertTypeBadge(a.type)}">${a.type}</span>
              <span class="inline-flex items-center rounded-full bg-white/10 px-2 py-0.5 text-[11px] font-semibold text-slate-200 ring-1 ring-white/10">sev ${a.severity}</span>
            </div>
            <div class="mt-2 text-sm text-slate-200">${a.description || "—"}</div>
            <div class="mt-1 text-xs text-slate-400">segment_id: ${a.segment_id}</div>
          </div>
          <button
            data-alert-id="${a.id}"
            class="shrink-0 rounded-lg bg-white/10 px-3 py-1 text-xs font-semibold text-white ring-1 ring-white/10 transition hover:bg-white/15"
            title="Закрыть алерт"
          >Закрыть</button>
        </div>
      `;
      container.appendChild(li);
    });

    container.querySelectorAll("button[data-alert-id]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = btn.getAttribute("data-alert-id");
        if (!id) return;
        btn.disabled = true;
        btn.textContent = "…";
        try {
          await resolveAlert(id);
          await loadAlerts();
          await loadTraffic();
        } catch (e) {
          console.error(e);
          btn.disabled = false;
          btn.textContent = "Ошибка";
        }
      });
    });
  } catch (e) {
    console.error(e);
    container.innerHTML =
      '<li class="rounded-xl bg-rose-500/10 p-3 text-rose-200 ring-1 ring-rose-500/30">Ошибка загрузки алертов</li>';
  }
}

async function loadMetrics() {
  const container = document.getElementById("metrics-list");
  container.innerHTML = "";
  try {
    const metrics = await fetchJSON("/api/metrics/summary?limit=5");
    if (!metrics.length) {
      container.innerHTML =
        '<li class="rounded-xl bg-slate-950/50 p-3 text-slate-300 ring-1 ring-white/10">Метрики пока не рассчитаны</li>';
      return;
    }
    metrics.forEach((m) => {
      const li = document.createElement("li");
      li.className = "rounded-xl bg-slate-950/50 p-3 ring-1 ring-white/10";
      li.innerHTML = `
        <div class="flex items-center justify-between gap-3">
          <div>
            <div class="text-xs font-semibold text-slate-200">Сегмент ${m.segment_id}</div>
            <div class="mt-1 text-xs text-slate-400">${m.time_window} · ${m.period_end}</div>
          </div>
          <div class="text-right">
            <div class="text-sm font-semibold text-slate-100">${m.congestion_index.toFixed(1)}</div>
            <div class="text-xs text-slate-400">avg_flow ${m.average_flow.toFixed(1)}</div>
          </div>
        </div>
      `;
      container.appendChild(li);
    });
  } catch (e) {
    console.error(e);
    container.innerHTML =
      '<li class="rounded-xl bg-rose-500/10 p-3 text-rose-200 ring-1 ring-rose-500/30">Ошибка загрузки метрик</li>';
  }
}

async function refreshAll() {
  // Make segment KPI resilient: update it after traffic load finishes.
  try {
    await loadTraffic();
  } finally {
    setText("kpi-segments", String(Array.isArray(latestSnapshots) ? latestSnapshots.length : 0));
  }
  await Promise.all([loadAlerts(), loadMetrics()]);
}

document.getElementById("refresh-btn").addEventListener("click", () => {
  refreshAll();
});

setSelected(null);
refreshAll();
setInterval(refreshAll, 15000);

