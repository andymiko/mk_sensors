<script setup>
import { computed, onMounted, reactive } from "vue";
import { useToast } from "primevue/usetoast";
import Button from "primevue/button";
import Column from "primevue/column";
import DataTable from "primevue/datatable";
import DatePicker from "primevue/datepicker";
import Message from "primevue/message";
import Select from "primevue/select";
import Tag from "primevue/tag";
import { useAssignmentsStore } from "../stores/assignments";
import { useAuthStore } from "../stores/auth";
import { useMonitoringStore } from "../stores/monitoring";

const assignments = useAssignmentsStore();
const auth = useAuthStore();
const monitoring = useMonitoringStore();
const toast = useToast();
const form = reactive({ object_id: null, channel_id: null, technician_id: null, scheduled_date: null });

const canCreate = computed(() => auth.hasPermission("assignment.create"));
const canComplete = computed(() => auth.hasPermission("assignment.complete"));
const pendingMine = computed(() => assignments.items.filter(
  (item) => item.status === "pending" && item.technician_id === auth.user?.id,
).length);
const objectOptions = computed(() => monitoring.objects.map((item) => ({
  label: item.dispatch_name,
  value: item.id,
})));
const technicianOptions = computed(() => assignments.technicians.map((item) => ({
  label: `${item.name} · ${item.email}`,
  value: item.id,
})));
const channelOptions = computed(() => assignments.channels.map((item) => ({
  label: item.sensor_name || `Канал ${item.id}`,
  value: item.id,
})));

function dateValue(value) {
  if (!(value instanceof Date)) return null;
  const part = (number) => String(number).padStart(2, "0");
  return `${value.getFullYear()}-${part(value.getMonth() + 1)}-${part(value.getDate())}`;
}

async function changeObject() {
  form.channel_id = null;
  form.technician_id = null;
  try {
    await assignments.loadOptions(form.object_id);
  } catch (error) {
    toast.add({ severity: "error", summary: "Не удалось загрузить данные", detail: error.message, life: 4000 });
  }
}

async function submit() {
  if (!form.object_id || !form.technician_id || !form.scheduled_date) return;
  try {
    await assignments.create({
      object_id: form.object_id,
      channel_id: form.channel_id,
      technician_id: form.technician_id,
      scheduled_date: dateValue(form.scheduled_date),
    });
    Object.assign(form, { object_id: null, channel_id: null, technician_id: null, scheduled_date: null });
    assignments.clearOptions();
    toast.add({ severity: "success", summary: "Задание назначено", detail: "Техник увидит его в разделе «Назначения».", life: 3500 });
  } catch (error) {
    toast.add({ severity: "error", summary: "Не удалось назначить", detail: error.message, life: 5000 });
  }
}

async function complete(item) {
  try {
    await assignments.complete(item.id);
    toast.add({ severity: "success", summary: "Задание выполнено", life: 3000 });
  } catch (error) {
    toast.add({ severity: "error", summary: "Не удалось завершить", detail: error.message, life: 5000 });
  }
}

function formatDate(value) {
  return new Date(`${value}T00:00:00`).toLocaleDateString("ru-RU");
}

onMounted(async () => {
  const requests = [assignments.load()];
  if (canCreate.value) requests.push(monitoring.loadObjects());
  await Promise.allSettled(requests);
});
</script>

<template>
  <section class="page-stack assignments-page">
    <div class="page-title-row">
      <div class="page-title">
        <span class="eyebrow">РАБОТЫ</span>
        <h1>Назначения</h1>
        <p>Проверки объектов и датчиков, назначенные техническим специалистам.</p>
      </div>
      <span class="result-count">{{ assignments.items.length }} заданий</span>
    </div>

    <Message v-if="pendingMine" severity="info" :closable="false">
      {{ pendingMine === 1 ? "Вам назначено задание" : `Вам назначено заданий: ${pendingMine}` }}
    </Message>
    <Message v-if="assignments.error" severity="error">{{ assignments.error }}</Message>

    <div v-if="canCreate" class="section-card assignment-form">
      <div class="section-heading-inline">
        <div><span class="eyebrow">НОВОЕ ЗАДАНИЕ</span><h2>Назначить проверку</h2></div>
        <span class="muted-text">Один объект можно назначить только один раз на выбранную дату</span>
      </div>
      <div class="assignment-fields">
        <label>Объект<Select v-model="form.object_id" :options="objectOptions" option-label="label" option-value="value" filter placeholder="Выберите объект" @change="changeObject" /></label>
        <label>Датчик<Select v-model="form.channel_id" :options="channelOptions" option-label="label" option-value="value" show-clear :disabled="!form.object_id" placeholder="Весь объект" /></label>
        <label>Техник<Select v-model="form.technician_id" :options="technicianOptions" option-label="label" option-value="value" filter :disabled="!form.object_id" placeholder="Выберите техника" /></label>
        <label>Дата<DatePicker v-model="form.scheduled_date" date-format="dd.mm.yy" show-icon placeholder="Дата проверки" /></label>
        <Button label="Назначить" icon="pi pi-send" :loading="assignments.saving" :disabled="!form.object_id || !form.technician_id || !form.scheduled_date" @click="submit" />
      </div>
    </div>

    <div class="section-card table-card">
      <DataTable :value="assignments.items" :loading="assignments.loading" paginator :rows="20" :rows-per-page-options="[10, 20, 50]" striped-rows responsive-layout="scroll">
        <Column field="scheduled_date" header="Дата" sortable><template #body="{ data }">{{ formatDate(data.scheduled_date) }}</template></Column>
        <Column field="object_name" header="Объект" sortable><template #body="{ data }"><strong>{{ data.object_name }}</strong><span class="table-subtitle">ID {{ data.object_id }}</span></template></Column>
        <Column header="Что проверить"><template #body="{ data }"><template v-if="data.channel_id">{{ data.sensor_name || `Канал ${data.channel_id}` }}<span class="table-subtitle">{{ data.sensor_type || "Тип не указан" }}</span></template><Tag v-else value="Весь объект" severity="secondary" /></template></Column>
        <Column field="technician_name" header="Техник" sortable />
        <Column field="dispatcher_name" header="Диспетчер" />
        <Column field="status" header="Статус" sortable><template #body="{ data }"><Tag :value="data.status === 'completed' ? 'Выполнено' : 'Назначено'" :severity="data.status === 'completed' ? 'success' : 'warn'" /></template></Column>
        <Column v-if="canComplete || auth.isAdmin" header="Действия" frozen align-frozen="right"><template #body="{ data }"><Button v-if="data.status === 'pending' && (data.technician_id === auth.user?.id || auth.isAdmin)" label="Задание выполнено" icon="pi pi-check" size="small" severity="success" :loading="assignments.saving" @click="complete(data)" /><span v-else>—</span></template></Column>
        <template #empty>Заданий пока нет.</template>
      </DataTable>
    </div>
  </section>
</template>
