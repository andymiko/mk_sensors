<script setup>
import { computed, onMounted, reactive } from "vue";
import Button from "primevue/button";
import Column from "primevue/column";
import DataTable from "primevue/datatable";
import DatePicker from "primevue/datepicker";
import Message from "primevue/message";
import Select from "primevue/select";
import Tag from "primevue/tag";
import { useMonitoringStore } from "../stores/monitoring";

const monitoring = useMonitoringStore();
const filters = reactive({ dateFrom: null, dateTo: null, objectId: null, sensorType: null });
const objectOptions = computed(() =>
  monitoring.objects.map((item) => ({ label: item.dispatch_name, value: item.id })),
);
const sensorOptions = computed(() =>
  [...new Set(monitoring.channels.map((item) => item.sensor_type).filter(Boolean))]
    .sort()
    .map((value) => ({ label: value, value })),
);

function iso(value) {
  if (!(value instanceof Date)) return null;
  const part = (number) => String(number).padStart(2, "0");
  return `${value.getFullYear()}-${part(value.getMonth() + 1)}-${part(value.getDate())}T${part(value.getHours())}:${part(value.getMinutes())}:${part(value.getSeconds())}`;
}
function load() {
  return monitoring.loadEvents({
    date_from: iso(filters.dateFrom),
    date_to: iso(filters.dateTo),
    object_id: filters.objectId,
    sensor_type: filters.sensorType,
  });
}
function reset() {
  Object.assign(filters, { dateFrom: null, dateTo: null, objectId: null, sensorType: null });
  load();
}
onMounted(async () => {
  await Promise.all([monitoring.loadObjects(), monitoring.loadChannels()]);
  await load();
});
</script>

<template>
  <section class="page-stack">
    <div class="page-title-row">
      <div class="page-title">
        <span class="eyebrow">МОНИТОРИНГ</span>
        <h1>Текущие показания</h1>
        <p>События каналов с фильтрацией по периоду, объекту и типу датчика.</p>
      </div>
      <span class="result-count">{{ monitoring.eventTotal }} событий</span>
    </div>
    <div class="section-card filter-grid" aria-label="Фильтры показаний">
      <label>С даты<DatePicker v-model="filters.dateFrom" show-time hour-format="24" /></label>
      <label>По дату<DatePicker v-model="filters.dateTo" show-time hour-format="24" /></label>
      <label>Объект<Select v-model="filters.objectId" :options="objectOptions" option-label="label" option-value="value" show-clear filter /></label>
      <label>Тип датчика<Select v-model="filters.sensorType" :options="sensorOptions" option-label="label" option-value="value" show-clear /></label>
      <div class="filter-actions">
        <Button label="Применить" icon="pi pi-filter" @click="load" />
        <Button label="Сбросить" severity="secondary" text @click="reset" />
      </div>
    </div>
    <Message v-if="monitoring.error" severity="error">{{ monitoring.error }}</Message>
    <div class="section-card table-card">
      <DataTable :value="monitoring.events" :loading="monitoring.loadingEvents" striped-rows responsive-layout="scroll">
        <Column field="event_at" header="Дата события">
          <template #body="{ data }">{{ new Date(data.event_at).toLocaleString("ru-RU") }}</template>
        </Column>
        <Column field="object_id" header="Объект" />
        <Column field="sensor_type" header="Тип датчика" />
        <Column field="sensor_name" header="Датчик" />
        <Column field="sensor_value" header="Значение">
          <template #body="{ data }">{{ data.sensor_value ?? "—" }}</template>
        </Column>
        <Column header="Статус">
          <template #body="{ data }"><Tag :value="data.is_alarm ? 'Тревога' : 'Норма'" :severity="data.is_alarm ? 'danger' : 'success'" /></template>
        </Column>
        <template #empty>Показания по выбранным условиям не найдены.</template>
      </DataTable>
    </div>
  </section>
</template>
