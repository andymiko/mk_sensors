<script setup>
import { computed, onMounted, reactive } from "vue";
import { useToast } from "primevue/usetoast";
import Button from "primevue/button";
import Checkbox from "primevue/checkbox";
import Column from "primevue/column";
import DataTable from "primevue/datatable";
import DatePicker from "primevue/datepicker";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import Select from "primevue/select";
import Tag from "primevue/tag";
import { useAuthStore } from "../stores/auth";
import { useForecastsStore } from "../stores/forecasts";

const auth = useAuthStore();
const forecasts = useForecastsStore();
const toast = useToast();
const form = reactive({ channel_id: null, event_at: new Date(), sensor_value: "", is_alarm: false });
const canCreate = computed(() => auth.hasPermission("forecast.create"));
const channelOptions = computed(() => forecasts.channels.map((item) => ({
  ...item,
  label: `${item.object_name} · ${item.sensor_name || `Канал ${item.id}`}${item.model_key ? "" : " · без модели"}`,
})));

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

async function submit() {
  if (!form.channel_id || !form.event_at) return;
  try {
    const result = await forecasts.create({
      channel_id: form.channel_id,
      event_at: localIso(form.event_at),
      sensor_value: form.sensor_value || null,
      is_alarm: form.is_alarm,
    });
    form.sensor_value = "";
    form.is_alarm = false;
    form.event_at = new Date();
    toast.add({
      severity: result.status === "unsupported_channel" ? "info" : result.warning ? "warn" : "success",
      summary: result.status === "unsupported_channel" ? "Показание сохранено" : "Прогноз рассчитан",
      detail: conclusion(result),
      life: 5000,
    });
  } catch (error) {
    toast.add({ severity: "error", summary: "Не удалось построить прогноз", detail: error.message, life: 5000 });
  }
}

function formatDate(value) {
  return value ? new Date(value).toLocaleString("ru-RU") : "—";
}

onMounted(async () => {
  const requests = [forecasts.load()];
  if (canCreate.value) requests.push(forecasts.loadChannels());
  await Promise.allSettled(requests);
});
</script>

<template>
  <section class="page-stack forecasts-page">
    <div class="page-title-row">
      <div class="page-title">
        <span class="eyebrow">ПРОГНОЗИРОВАНИЕ</span>
        <h1>Журнал прогнозов</h1>
        <p>Вероятность состояния «Неисправен» в период от 1 до 31 дня после показания.</p>
      </div>
      <span class="result-count">{{ forecasts.items.length }} прогнозов</span>
    </div>

    <Message v-if="forecasts.error" severity="error">{{ forecasts.error }}</Message>

    <div v-if="canCreate" class="section-card forecast-form">
      <div class="section-heading-inline">
        <div><span class="eyebrow">НОВОЕ ПОКАЗАНИЕ</span><h2>Сохранить и построить прогноз</h2></div>
        <span class="muted-text">Модель выбирается автоматически по датчику</span>
      </div>
      <div class="forecast-fields">
        <label>Датчик<Select v-model="form.channel_id" :options="channelOptions" option-label="label" option-value="id" filter placeholder="Выберите датчик" /></label>
        <label>Дата и время<DatePicker v-model="form.event_at" show-time hour-format="24" show-icon /></label>
        <label>Значение<InputText v-model="form.sensor_value" placeholder="Например: Исправен" /></label>
        <label class="forecast-alarm"><Checkbox v-model="form.is_alarm" binary />Тревожное показание</label>
        <Button label="Сохранить и рассчитать" icon="pi pi-chart-line" :loading="forecasts.saving" :disabled="!form.channel_id || !form.event_at" @click="submit" />
      </div>
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
        <template #empty>Прогнозов пока нет.</template>
      </DataTable>
    </div>
  </section>
</template>
