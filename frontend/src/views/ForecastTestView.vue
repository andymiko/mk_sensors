<script setup>
import { computed, onMounted, reactive } from "vue";
import { useToast } from "primevue/usetoast";
import Button from "primevue/button";
import Checkbox from "primevue/checkbox";
import DatePicker from "primevue/datepicker";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import Select from "primevue/select";
import { useForecastsStore } from "../stores/forecasts";

const forecasts = useForecastsStore();
const toast = useToast();
const form = reactive({ channel_id: null, event_at: new Date(), sensor_value: "", is_alarm: false });
const channelOptions = computed(() => forecasts.channels.map((item) => ({
  ...item,
  label: `${item.object_name} · ${item.sensor_name || `Канал ${item.id}`}${item.model_key ? "" : " · без модели"}`,
})));

function localIso(value) {
  if (!(value instanceof Date)) return null;
  const part = (number) => String(number).padStart(2, "0");
  return `${value.getFullYear()}-${part(value.getMonth() + 1)}-${part(value.getDate())}T${part(value.getHours())}:${part(value.getMinutes())}:${part(value.getSeconds())}`;
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
    toast.add({
      severity: result.warning ? "warn" : "success",
      summary: "Показание сохранено, прогноз рассчитан",
      life: 4500,
    });
    Object.assign(form, { channel_id: null, event_at: new Date(), sensor_value: "", is_alarm: false });
  } catch (error) {
    toast.add({ severity: "error", summary: "Не удалось построить прогноз", detail: error.message, life: 5000 });
  }
}

onMounted(() => forecasts.loadChannels());
</script>

<template>
  <section class="page-stack forecasts-page">
    <div class="page-title">
      <span class="eyebrow">ТЕСТИРОВАНИЕ МОДЕЛИ</span>
      <h1>Новое показание</h1>
      <p>Сохранение тестового показания и запуск подходящей модели прогнозирования.</p>
    </div>
    <Message v-if="forecasts.error" severity="error">{{ forecasts.error }}</Message>
    <div class="section-card forecast-form">
      <div class="forecast-fields">
        <label>Датчик<Select v-model="form.channel_id" :options="channelOptions" option-label="label" option-value="id" filter placeholder="Выберите датчик" /></label>
        <label>Дата и время<DatePicker v-model="form.event_at" date-format="dd.mm.yy" show-time hour-format="24" show-icon /></label>
        <label>Значение<InputText v-model="form.sensor_value" placeholder="Например: Исправен" /></label>
        <label class="forecast-alarm"><Checkbox v-model="form.is_alarm" binary />Тревожное показание</label>
        <Button label="Сохранить и рассчитать" icon="pi pi-chart-line" :loading="forecasts.saving" :disabled="!form.channel_id || !form.event_at" @click="submit" />
      </div>
    </div>
  </section>
</template>
