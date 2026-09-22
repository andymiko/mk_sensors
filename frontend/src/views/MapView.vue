<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import * as maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import Message from "primevue/message";
import Dialog from "primevue/dialog";
import Column from "primevue/column";
import DataTable from "primevue/datatable";
import Tag from "primevue/tag";
import EmptyState from "../components/EmptyState.vue";
import { useMonitoringStore } from "../stores/monitoring";

const monitoring = useMonitoringStore();
const mapContainer = ref(null);
const mapError = ref("");
const selectedObject = ref(null);
const mapTileUrl =
  import.meta.env.VITE_MAP_TILE_URL ||
  "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
let map;

const mapStyle = {
  version: 8,
  sources: {
    openStreetMap: {
      type: "raster",
      tiles: [mapTileUrl],
      tileSize: 256,
      attribution: "© OpenStreetMap contributors",
    },
  },
  layers: [
    {
      id: "open-street-map",
      type: "raster",
      source: "openStreetMap",
    },
  ],
};

function geojson() {
  return {
    type: "FeatureCollection",
    features: monitoring.mapObjects
      .filter((item) => item.longitude != null && item.latitude != null)
      .map((item) => ({
        type: "Feature",
        geometry: { type: "Point", coordinates: [item.longitude, item.latitude] },
        properties: {
          id: item.id,
          name: item.dispatch_name,
          type: item.object_type,
          statusColor: item.status_color,
        },
      })),
  };
}

function renderMap() {
  const data = geojson();
  if (!data.features.length) return;
  map = new maplibregl.Map({
    container: mapContainer.value,
    style: mapStyle,
    center: [37.6176, 55.7558],
    zoom: 10,
    attributionControl: true,
  });
  map.addControl(new maplibregl.NavigationControl(), "top-right");
  map.on("load", () => {
    map.addSource("objects", { type: "geojson", data });
    map.addLayer({
      id: "objects",
      type: "circle",
      source: "objects",
      paint: {
        "circle-radius": 7,
        "circle-color": [
          "match",
          ["get", "statusColor"],
          "red", "#dc2626",
          "orange", "#f97316",
          "green", "#16a34a",
          "#64748b",
        ],
        "circle-stroke-width": 2,
        "circle-stroke-color": "#ffffff",
      },
    });
    const bounds = new maplibregl.LngLatBounds();
    data.features.forEach((feature) => bounds.extend(feature.geometry.coordinates));
    map.fitBounds(bounds, { padding: 64, maxZoom: 14 });
    map.on("click", "objects", (event) => {
      const objectId = Number(event.features?.[0]?.properties?.id);
      selectedObject.value = monitoring.mapObjects.find((item) => item.id === objectId) || null;
    });
    map.on("mouseenter", "objects", () => { map.getCanvas().style.cursor = "pointer"; });
    map.on("mouseleave", "objects", () => { map.getCanvas().style.cursor = ""; });
  });
  map.on("error", () => {
    mapError.value = "Не удалось загрузить картографическую подложку.";
  });
}

onMounted(async () => {
  await monitoring.loadMapObjects();
  await nextTick();
  renderMap();
});
onBeforeUnmount(() => map?.remove());
</script>

<template>
  <section class="page-stack map-page">
    <div class="page-title-row">
      <div class="page-title">
        <span class="eyebrow">ГЕОГРАФИЯ</span>
        <h1>Карта объектов</h1>
        <p>Объекты с доступными координатами из справочника Objects.</p>
      </div>
      <span class="result-count">{{ monitoring.objectTotal }} объектов</span>
    </div>
    <Message v-if="monitoring.error || mapError" severity="error">{{ monitoring.error || mapError }}</Message>
    <div v-if="monitoring.loadingObjects" class="section-card map-loading" aria-busy="true">Загрузка объектов…</div>
    <div v-else-if="!monitoring.mapObjects.some((item) => item.longitude != null && item.latitude != null)" class="section-card">
      <EmptyState icon="pi-map-marker" title="Нет объектов с координатами" text="Добавьте широту и долготу объектам, чтобы показать их на карте." />
    </div>
    <div v-else class="map-stage">
      <div ref="mapContainer" class="object-map" aria-label="Интерактивная карта объектов" />
      <div class="map-legend" aria-label="Легенда карты">
        <span><i class="status-dot green" />Норма</span>
        <span><i class="status-dot orange" />Есть отклонения</span>
        <span><i class="status-dot red" />Более 30% отклонений</span>
      </div>
    </div>
    <Dialog :visible="Boolean(selectedObject)" modal :header="selectedObject?.dispatch_name" class="object-card-dialog" @update:visible="selectedObject = null">
      <div v-if="selectedObject" class="page-stack">
        <div class="object-summary">
          <span>ID {{ selectedObject.id }}</span>
          <span>{{ selectedObject.district_name || "Район не назначен" }}</span>
          <Tag :value="selectedObject.status" :severity="selectedObject.status_color === 'red' ? 'danger' : selectedObject.status_color === 'orange' ? 'warn' : 'success'" />
        </div>
        <DataTable :value="selectedObject.sensors" size="small" striped-rows responsive-layout="scroll">
          <Column field="sensor_name" header="Датчик">
            <template #body="{ data }">{{ data.sensor_name || `Канал ${data.channel_id}` }}</template>
          </Column>
          <Column field="sensor_type" header="Тип" />
          <Column field="sensor_value" header="Текущее значение">
            <template #body="{ data }">{{ data.sensor_value ?? "—" }}</template>
          </Column>
          <Column field="status" header="Статус">
            <template #body="{ data }"><Tag :value="data.status" :severity="data.is_alarm == null ? 'secondary' : data.is_alarm ? 'danger' : 'success'" /></template>
          </Column>
          <Column field="event_at" header="Дата события">
            <template #body="{ data }">{{ data.event_at ? new Date(data.event_at).toLocaleString("ru-RU") : "—" }}</template>
          </Column>
          <template #empty>К объекту не привязаны датчики.</template>
        </DataTable>
      </div>
    </Dialog>
  </section>
</template>
