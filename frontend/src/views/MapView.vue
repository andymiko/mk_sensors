<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import * as maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import Message from "primevue/message";
import EmptyState from "../components/EmptyState.vue";
import { useMonitoringStore } from "../stores/monitoring";

const monitoring = useMonitoringStore();
const mapContainer = ref(null);
const mapError = ref("");
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
    features: monitoring.objects
      .filter((item) => item.longitude != null && item.latitude != null)
      .map((item) => ({
        type: "Feature",
        geometry: { type: "Point", coordinates: [item.longitude, item.latitude] },
        properties: { id: item.id, name: item.dispatch_name, type: item.object_type },
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
        "circle-color": "#2563eb",
        "circle-stroke-width": 2,
        "circle-stroke-color": "#ffffff",
      },
    });
    const bounds = new maplibregl.LngLatBounds();
    data.features.forEach((feature) => bounds.extend(feature.geometry.coordinates));
    map.fitBounds(bounds, { padding: 64, maxZoom: 14 });
  });
  map.on("error", () => {
    mapError.value = "Не удалось загрузить картографическую подложку.";
  });
}

onMounted(async () => {
  await monitoring.loadObjects();
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
    <div v-else-if="!monitoring.objects.some((item) => item.longitude != null && item.latitude != null)" class="section-card">
      <EmptyState icon="pi-map-marker" title="Нет объектов с координатами" text="Добавьте широту и долготу объектам, чтобы показать их на карте." />
    </div>
    <div v-else ref="mapContainer" class="object-map" aria-label="Интерактивная карта объектов" />
  </section>
</template>
