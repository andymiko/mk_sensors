<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { LngLatBounds, Map, setWorkerUrl } from "maplibre-gl";
import maplibreWorkerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url";
import "maplibre-gl/dist/maplibre-gl.css";
import Button from "primevue/button";
import Message from "primevue/message";
import Tag from "primevue/tag";
import EmptyState from "../components/EmptyState.vue";
import { useMonitoringStore } from "../stores/monitoring";

const monitoring = useMonitoringStore();
const router = useRouter();
const mapContainer = ref(null);
const mapError = ref("");
let map;

setWorkerUrl(maplibreWorkerUrl);

const summary = computed(() => monitoring.dashboard);
const abnormalObjects = computed(() =>
  (summary.value?.objects || []).filter((item) => item.status_color !== "green"),
);
const mapObjects = computed(() =>
  (summary.value?.objects || []).filter(
    (item) => item.longitude != null && item.latitude != null,
  ),
);
const cards = computed(() => [
  { label: "Объекты на контроле", value: summary.value?.total_objects ?? 0, icon: "pi-building", tone: "blue" },
  { label: "Объекты с отклонениями", value: summary.value?.abnormal_objects ?? 0, icon: "pi-exclamation-triangle", tone: "orange" },
  { label: "Более 30% отклонений", value: summary.value?.critical_objects ?? 0, icon: "pi-bolt", tone: "red" },
  { label: "Датчики на контроле", value: summary.value?.total_sensors ?? 0, icon: "pi-wave-pulse", tone: "teal" },
  { label: "Диспетчеры", value: summary.value?.dispatcher_count ?? 0, icon: "pi-headphones", tone: "violet" },
  { label: "Техники", value: summary.value?.technician_count ?? 0, icon: "pi-wrench", tone: "slate" },
]);

function abnormalSensors(item) {
  return item.sensors.filter((sensor) => sensor.is_alarm !== false);
}

function renderMap() {
  if (!mapContainer.value || !mapObjects.value.length) return;
  const data = {
    type: "FeatureCollection",
    features: mapObjects.value.map((item) => ({
      type: "Feature",
      geometry: { type: "Point", coordinates: [item.longitude, item.latitude] },
      properties: { statusColor: item.status_color },
    })),
  };
  map = new Map({
    container: mapContainer.value,
    style: {
      version: 8,
      sources: {
        openStreetMap: {
          type: "raster",
          tiles: [import.meta.env.VITE_MAP_TILE_URL || "https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
          tileSize: 256,
          attribution: "© OpenStreetMap contributors",
        },
      },
      layers: [{ id: "open-street-map", type: "raster", source: "openStreetMap" }],
    },
    center: [37.6176, 55.7558],
    zoom: 9,
    attributionControl: false,
    interactive: false,
  });
  map.on("load", () => {
    map.addSource("dashboard-objects", { type: "geojson", data });
    map.addLayer({
      id: "dashboard-objects",
      type: "circle",
      source: "dashboard-objects",
      paint: {
        "circle-radius": 6,
        "circle-color": [
          "match", ["get", "statusColor"],
          "red", "#dc2626", "orange", "#f97316", "green", "#16a34a", "#64748b",
        ],
        "circle-stroke-width": 2,
        "circle-stroke-color": "#ffffff",
      },
    });
    const bounds = new LngLatBounds();
    data.features.forEach((feature) => bounds.extend(feature.geometry.coordinates));
    map.fitBounds(bounds, { padding: 42, maxZoom: 13, duration: 0 });
  });
  map.on("error", () => {
    mapError.value = "Не удалось загрузить картографическую подложку.";
  });
}

async function refreshDashboard() {
  try {
    mapError.value = "";
    await monitoring.loadDashboard();
    map?.remove();
    map = undefined;
    await nextTick();
    renderMap();
  } catch {
    // Store exposes the request error in the page message.
  }
}

onMounted(refreshDashboard);
onBeforeUnmount(() => map?.remove());
</script>

<template>
  <section class="page-stack dashboard-page">
    <div class="page-title-row">
      <div class="page-title">
        <span class="eyebrow">АНАЛИТИКА</span>
        <h1>Дашборд</h1>
        <p>Текущее состояние доступных объектов и обслуживающих подразделений.</p>
      </div>
      <Button icon="pi pi-refresh" label="Обновить" severity="secondary" outlined :loading="monitoring.loadingDashboard" @click="refreshDashboard" />
    </div>

    <Message v-if="monitoring.error" severity="error">{{ monitoring.error }}</Message>
    <div v-if="monitoring.loadingDashboard && !summary" class="section-card dashboard-loading" aria-busy="true">Загрузка показателей…</div>

    <template v-else-if="summary">
      <div class="dashboard-kpis">
        <article v-for="card in cards" :key="card.label" class="section-card dashboard-kpi">
          <span class="dashboard-kpi-icon" :class="card.tone"><i class="pi" :class="card.icon" /></span>
          <div><strong>{{ card.value.toLocaleString("ru-RU") }}</strong><span>{{ card.label }}</span></div>
        </article>
      </div>

      <div class="dashboard-grid">
        <article class="section-card dashboard-map-card">
          <div class="dashboard-card-heading">
            <div><span class="eyebrow">ГЕОГРАФИЯ</span><h2>Объекты на карте</h2></div>
            <Button label="Открыть карту" icon="pi pi-arrow-right" icon-pos="right" text @click="router.push('/map')" />
          </div>
          <Message v-if="mapError" severity="warn">{{ mapError }}</Message>
          <div v-if="mapObjects.length" ref="mapContainer" class="dashboard-map" aria-label="Карта доступных объектов" />
          <EmptyState v-else icon="pi-map-marker" title="Нет объектов с координатами" text="Карта появится после заполнения координат объектов." />
          <div v-if="mapObjects.length" class="dashboard-map-legend">
            <span><i class="status-dot green" />Норма</span>
            <span><i class="status-dot orange" />Отклонения</span>
            <span><i class="status-dot red" />Более 30%</span>
          </div>
        </article>

        <article class="section-card dashboard-alerts">
          <div class="dashboard-card-heading">
            <div><span class="eyebrow">ТРЕБУЮТ ВНИМАНИЯ</span><h2>Объекты с отклонениями</h2></div>
            <Tag :value="abnormalObjects.length" :severity="abnormalObjects.length ? 'danger' : 'success'" rounded />
          </div>
          <div v-if="abnormalObjects.length" class="dashboard-alert-list">
            <div v-for="item in abnormalObjects" :key="item.id" class="dashboard-alert-item">
              <div class="dashboard-alert-title">
                <div><strong>{{ item.dispatch_name }}</strong><span>ID {{ item.id }} · {{ item.district_name || "Район не назначен" }}</span></div>
                <Tag :value="item.status" :severity="item.status_color === 'red' ? 'danger' : 'warn'" />
              </div>
              <ul>
                <li v-for="sensor in abnormalSensors(item)" :key="sensor.channel_id">
                  <span>{{ sensor.sensor_name || `Канал ${sensor.channel_id}` }}</span>
                  <strong>{{ sensor.status }}<template v-if="sensor.sensor_value != null"> · {{ sensor.sensor_value }}</template></strong>
                </li>
              </ul>
            </div>
          </div>
          <EmptyState v-else icon="pi-check-circle" title="Все объекты в норме" text="По последним показаниям отклонений не обнаружено." />
        </article>
      </div>
    </template>
  </section>
</template>
