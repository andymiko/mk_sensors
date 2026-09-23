<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { useRoute } from "vue-router";
import { useToast } from "primevue/usetoast";
import Button from "primevue/button";
import Column from "primevue/column";
import DataTable from "primevue/datatable";
import DatePicker from "primevue/datepicker";
import Message from "primevue/message";
import Select from "primevue/select";
import Tag from "primevue/tag";
import ReportButtons from "../components/ReportButtons.vue";
import { useAssignmentsStore } from "../stores/assignments";
import { useAuthStore } from "../stores/auth";
import { useMonitoringStore } from "../stores/monitoring";

const assignments = useAssignmentsStore();
const auth = useAuthStore();
const monitoring = useMonitoringStore();
const toast = useToast();
const route = useRoute();
const form = reactive({ object_id: null, channel_id: null, technician_id: null, scheduled_date: null });
const expandedAssignments = ref(new Set());

const canCreate = computed(() => auth.hasPermission("assignment.create"));
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
  label: `${item.sensor_name || `Канал ${item.id}`} · ${item.sensor_type || "Тип не указан"}`,
  name: item.sensor_name || `Канал ${item.id}`,
  type: item.sensor_type || "Тип не указан",
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

async function completeSensor(assignment, sensor) {
  try {
    await assignments.completeItem(assignment.id, sensor.id);
    toast.add({ severity: "success", summary: "Датчик проверен", life: 3000 });
  } catch (error) {
    toast.add({ severity: "error", summary: "Не удалось завершить проверку", detail: error.message, life: 5000 });
  }
}

function canCompleteSensor(assignment, sensor) {
  return sensor.status === "pending" &&
    (assignment.technician_id === auth.user?.id || auth.isAdmin);
}

function formatDate(value) {
  return new Date(`${value}T00:00:00`).toLocaleDateString("ru-RU");
}

function toggleSensors(assignmentId) {
  const next = new Set(expandedAssignments.value);
  if (next.has(assignmentId)) next.delete(assignmentId);
  else next.add(assignmentId);
  expandedAssignments.value = next;
}

onMounted(async () => {
  const requests = [assignments.load()];
  if (canCreate.value) requests.push(monitoring.loadObjects());
  await Promise.allSettled(requests);
  if (canCreate.value && route.query.object_id) {
    form.object_id = Number(route.query.object_id);
    await changeObject();
    if (route.query.channel_id) form.channel_id = Number(route.query.channel_id);
  }
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
      <div class="page-title-actions"><ReportButtons dataset="assignments" /><span class="result-count">{{ assignments.items.length }} заданий</span></div>
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
        <label>Что проверить<Select v-model="form.channel_id" :options="channelOptions" option-label="label" option-value="value" show-clear filter :disabled="!form.object_id" placeholder="Весь объект"><template #option="{ option }"><div><strong>{{ option.name }}</strong><span class="table-subtitle">Тип: {{ option.type }}</span></div></template></Select></label>
        <label>Техник<Select v-model="form.technician_id" :options="technicianOptions" option-label="label" option-value="value" filter :disabled="!form.object_id" placeholder="Выберите техника" /></label>
        <label>Дата<DatePicker v-model="form.scheduled_date" date-format="dd.mm.yy" show-icon placeholder="Дата проверки" /></label>
        <Button label="Назначить" icon="pi pi-send" :loading="assignments.saving" :disabled="!form.object_id || !form.technician_id || !form.scheduled_date" @click="submit" />
      </div>
    </div>

    <div class="section-card table-card">
      <DataTable :value="assignments.items" :loading="assignments.loading" paginator :rows="20" :rows-per-page-options="[10, 20, 50]" striped-rows responsive-layout="scroll">
        <Column field="scheduled_date" header="Дата" sortable><template #body="{ data }">{{ formatDate(data.scheduled_date) }}</template></Column>
        <Column field="object_name" header="Объект" sortable><template #body="{ data }"><strong>{{ data.object_name }}</strong><span class="table-subtitle">ID {{ data.object_id }}</span></template></Column>
        <Column header="Что проверить"><template #body="{ data }"><div class="assignment-object-sensors"><button v-if="!data.channel_id" type="button" class="assignment-expand-button" :aria-expanded="expandedAssignments.has(data.id)" @click="toggleSensors(data.id)"><span>Весь объект</span><i class="pi" :class="expandedAssignments.has(data.id) ? 'pi-chevron-up' : 'pi-chevron-down'" /></button><div v-if="data.channel_id || expandedAssignments.has(data.id)" class="assignment-sensor-list"><div v-for="sensor in data.sensors" :key="sensor.id" class="assignment-sensor-item"><div><strong>{{ sensor.name || `Канал ${sensor.id}` }}</strong><span class="table-subtitle">Тип: {{ sensor.type || "Не указан" }}</span></div><Tag v-if="sensor.status === 'completed'" value="Проверен" severity="success" /><Button v-else-if="canCompleteSensor(data, sensor)" label="Проверено" icon="pi pi-check" size="small" severity="success" :loading="assignments.saving" @click="completeSensor(data, sensor)" /><Tag v-else value="Ожидает проверки" severity="warn" /></div><span v-if="!data.sensors?.length" class="muted-text">На объекте нет датчиков</span></div></div></template></Column>
        <Column field="technician_name" header="Техник" sortable />
        <Column field="dispatcher_name" header="Диспетчер" />
        <Column field="status" header="Статус" sortable><template #body="{ data }"><Tag :value="data.status === 'completed' ? 'Выполнено' : 'Назначено'" :severity="data.status === 'completed' ? 'success' : 'warn'" /></template></Column>
        <template #empty>Заданий пока нет.</template>
      </DataTable>
    </div>
  </section>
</template>
