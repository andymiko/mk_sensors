<script setup>
import { computed, onMounted, reactive } from "vue";
import { useRouter } from "vue-router";
import Button from "primevue/button";
import Column from "primevue/column";
import DataTable from "primevue/datatable";
import DatePicker from "primevue/datepicker";
import Message from "primevue/message";
import Select from "primevue/select";
import Tag from "primevue/tag";
import ReportButtons from "../components/ReportButtons.vue";
import { useAuthStore } from "../stores/auth";
import { useForecastsStore } from "../stores/forecasts";

const auth = useAuthStore();
const forecasts = useForecastsStore();
const router = useRouter();
const filters = reactive({ dateFrom: null, dateTo: null, riskOrder: "desc" });
const riskOptions = [{ label: "Сначала высокий риск", value: "desc" }, { label: "Сначала низкий риск", value: "asc" }];
const reportParams = computed(() => ({ date_from: localIso(filters.dateFrom), date_to: localIso(filters.dateTo), risk_order: filters.riskOrder }));

const statusLabels = {
  insufficient_history: "Недостаточно истории",
  recent_alarm_failure: "Уже зарегистрирована неисправность",
  no_recent_object_data: "Нет свежих данных объекта",
  unsupported_channel: "Канал пока не поддерживается моделью",
};

function localIso(value) {
  if (!(value instanceof Date)) return null;
  const part = (number) => String(number).padStart(2, "0");
  return `${value.getFullYear()}-${part(value.getMonth() + 1)}-${part(value.getDate())}T${part(value.getHours())}:${part(value.getMinutes())}:${part(value.getSeconds())}`;
}

function conclusion(item) {
  if (item.status !== "ok") return statusLabels[item.status] || item.status;
  return item.warning ? "Возможна неисправность в ближайшие 30 дней" : "Неисправность в ближайшие 30 дней не прогнозируется";
}

function severity(item) {
  if (item.status !== "ok") return "secondary";
  return item.warning ? "danger" : "success";
}

function load() {
  return forecasts.load({ date_from: localIso(filters.dateFrom), date_to: localIso(filters.dateTo), risk_order: filters.riskOrder });
}
function reset() {
  Object.assign(filters, { dateFrom: null, dateTo: null, riskOrder: "desc" });
  load();
}
function makeAssignment(item) {
  router.push({ name: "assignments", query: { object_id: item.object_id, channel_id: item.channel_id } });
}

function formatDate(value) {
  return value ? new Date(value).toLocaleString("ru-RU") : "—";
}

onMounted(load);
</script>

<template>
  <section class="page-stack forecasts-page">
    <div class="page-title-row">
      <div class="page-title">
        <span class="eyebrow">ПРОГНОЗИРОВАНИЕ</span>
        <h1>Журнал прогнозов</h1>
        <p>Вероятность состояния «Неисправен» в период от 1 до 31 дня после показания.</p>
      </div>
      <div class="page-title-actions"><ReportButtons dataset="forecasts" :params="reportParams" /><span class="result-count">{{ forecasts.items.length }} прогнозов</span></div>
    </div>

    <Message v-if="forecasts.error" severity="error">{{ forecasts.error }}</Message>

    <div class="section-card filter-grid" aria-label="Фильтры прогнозов">
      <label>С даты<DatePicker v-model="filters.dateFrom" show-time hour-format="24" /></label>
      <label>По дату<DatePicker v-model="filters.dateTo" show-time hour-format="24" /></label>
      <label>Сортировка по риску<Select v-model="filters.riskOrder" :options="riskOptions" option-label="label" option-value="value" /></label>
      <div class="filter-actions"><Button label="Применить" icon="pi pi-filter" @click="load" /><Button label="Сбросить" severity="secondary" text @click="reset" /></div>
    </div>

    <div class="section-card table-card">
      <DataTable :value="forecasts.items" :loading="forecasts.loading" paginator :rows="20" :rows-per-page-options="[10, 20, 50]" striped-rows responsive-layout="scroll">
        <Column field="created_at" header="Создан" sortable><template #body="{ data }">{{ new Date(data.created_at * 1000).toLocaleString("ru-RU") }}</template></Column>
        <Column field="object_name" header="Объект" sortable><template #body="{ data }"><strong>{{ data.object_name }}</strong><span class="table-subtitle">ID {{ data.object_id }}</span></template></Column>
        <Column field="sensor_name" header="Датчик" sortable><template #body="{ data }">{{ data.sensor_name || `Канал ${data.channel_id}` }}<span class="table-subtitle">{{ data.sensor_type || "Тип не указан" }}</span></template></Column>
        <Column field="event_at" header="Показание"><template #body="{ data }">{{ data.sensor_value ?? "—" }}<span class="table-subtitle">{{ formatDate(data.event_at) }}</span></template></Column>
        <Column header="Период прогноза"><template #body="{ data }"><template v-if="data.status === 'ok'">{{ formatDate(data.target_from) }}<span class="table-subtitle">до {{ formatDate(data.target_until) }}</span></template><span v-else>—</span></template></Column>
        <Column header="Риск"><template #body="{ data }">{{ data.risk_score == null ? "—" : `${(data.risk_score * 100).toFixed(1)}%` }}</template></Column>
        <Column header="Результат"><template #body="{ data }"><Tag :value="conclusion(data)" :severity="severity(data)" /></template></Column>
        <Column v-if="auth.roleCodes.includes('dispatcher')" header="Действия"><template #body="{ data }"><Button v-if="data.warning" label="Сделать направление" icon="pi pi-send" size="small" @click="makeAssignment(data)" /><span v-else>—</span></template></Column>
        <template #empty>Прогнозов пока нет.</template>
      </DataTable>
    </div>
  </section>
</template>
