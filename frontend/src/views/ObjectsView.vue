<script setup>
import { computed, onMounted, ref } from "vue";
import Button from "primevue/button";
import Column from "primevue/column";
import DataTable from "primevue/datatable";
import Dialog from "primevue/dialog";
import InputNumber from "primevue/inputnumber";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import Select from "primevue/select";
import Tag from "primevue/tag";
import { apiRequest } from "../services/api";
import { useAuthStore } from "../stores/auth";
import { useMonitoringStore } from "../stores/monitoring";

const auth = useAuthStore();
const monitoring = useMonitoringStore();
const districts = ref([]);
const details = ref(null);
const editing = ref(false);
const form = ref({});
const saving = ref(false);
const districtOptions = computed(() =>
  districts.value.map((item) => ({ label: item.name, value: item.id })),
);

async function showDetails(object) {
  details.value = await monitoring.loadObjectDetails(object.id);
}

async function editObject(object) {
  const item = await monitoring.loadObjectDetails(object.id);
  form.value = {
    id: item.id,
    dispatch_name: item.dispatch_name,
    object_type: item.object_type,
    hierarchy_level: item.hierarchy_level,
    district_id: item.district_id,
    longitude: item.longitude,
    latitude: item.latitude,
  };
  editing.value = true;
}

async function save() {
  saving.value = true;
  try {
    const { id, ...payload } = form.value;
    await monitoring.updateObject(id, payload);
    editing.value = false;
    await monitoring.loadObjects();
  } finally {
    saving.value = false;
  }
}

function sort(event) {
  monitoring.loadObjects({
    sortBy: event.sortField || "id",
    sortOrder: event.sortOrder === -1 ? "desc" : "asc",
  });
}

onMounted(async () => {
  await monitoring.loadObjects();
  if (auth.hasPermission("object.edit")) {
    districts.value = await apiRequest("/admin/districts");
  }
});
</script>

<template>
  <section class="page-stack">
    <div class="page-title-row">
      <div class="page-title">
        <span class="eyebrow">ИНФРАСТРУКТУРА</span>
        <h1>Объекты контроля</h1>
        <p>Доступные объекты и их территориальная принадлежность.</p>
      </div>
      <span class="result-count">{{ monitoring.objectTotal }} объектов</span>
    </div>
    <Message v-if="monitoring.error" severity="error">{{ monitoring.error }}</Message>
    <div class="section-card table-card">
      <DataTable
        :value="monitoring.objects"
        :loading="monitoring.loadingObjects"
        sort-mode="single"
        removable-sort
        striped-rows
        responsive-layout="scroll"
        @sort="sort"
      >
        <Column header="Действия" frozen>
          <template #body="{ data }">
            <div class="object-actions">
              <Button label="Об объекте" icon="pi pi-eye" size="small" outlined @click="showDetails(data)" />
              <Button v-if="auth.hasPermission('object.edit')" label="Редактировать" icon="pi pi-pencil" size="small" @click="editObject(data)" />
            </div>
          </template>
        </Column>
        <Column field="dispatch_name" header="Название" sortable />
        <Column field="id" header="ID" sortable />
        <Column field="district_name" header="Район">
          <template #body="{ data }">{{ data.district_name || "Не назначен" }}</template>
        </Column>
        <template #empty>Доступные объекты не найдены.</template>
      </DataTable>
    </div>

    <Dialog :visible="Boolean(details)" modal :header="details?.dispatch_name" class="object-card-dialog" @update:visible="details = null">
      <div v-if="details" class="page-stack">
        <dl class="details-grid">
          <div><dt>ID</dt><dd>{{ details.id }}</dd></div>
          <div><dt>Тип</dt><dd>{{ details.object_type }}</dd></div>
          <div><dt>Уровень</dt><dd>{{ details.hierarchy_level }}</dd></div>
          <div><dt>Район</dt><dd>{{ details.district_name || "Не назначен" }}</dd></div>
          <div><dt>Координаты</dt><dd>{{ details.latitude ?? "—" }}, {{ details.longitude ?? "—" }}</dd></div>
          <div><dt>Состояние</dt><dd><Tag :value="details.status" :severity="details.status_color === 'red' ? 'danger' : details.status_color === 'orange' ? 'warn' : 'success'" /></dd></div>
        </dl>
        <h3>Датчики объекта</h3>
        <DataTable :value="details.sensors" size="small" striped-rows responsive-layout="scroll">
          <Column field="sensor_name" header="Датчик" />
          <Column field="sensor_type" header="Тип" />
          <Column field="sensor_value" header="Значение" />
          <Column field="status" header="Статус">
            <template #body="{ data }"><Tag :value="data.status" :severity="data.is_alarm == null ? 'secondary' : data.is_alarm ? 'danger' : 'success'" /></template>
          </Column>
          <Column field="event_at" header="Дата">
            <template #body="{ data }">{{ data.event_at ? new Date(data.event_at).toLocaleString("ru-RU") : "—" }}</template>
          </Column>
          <template #empty>Датчики не привязаны.</template>
        </DataTable>
      </div>
    </Dialog>

    <Dialog v-model:visible="editing" modal header="Редактировать объект" class="editor-dialog object-editor">
      <div class="form-grid">
        <label>ID<InputNumber v-model="form.id" disabled :use-grouping="false" /></label>
        <label>Название<InputText v-model="form.dispatch_name" /></label>
        <label>Тип<InputText v-model="form.object_type" /></label>
        <label>Уровень<InputNumber v-model="form.hierarchy_level" /></label>
        <label>Район<Select v-model="form.district_id" :options="districtOptions" option-label="label" option-value="value" filter show-clear /></label>
        <label>Широта<InputNumber v-model="form.latitude" :min-fraction-digits="0" :max-fraction-digits="8" /></label>
        <label>Долгота<InputNumber v-model="form.longitude" :min-fraction-digits="0" :max-fraction-digits="8" /></label>
      </div>
      <template #footer><Button label="Сохранить" icon="pi pi-check" :loading="saving" @click="save" /></template>
    </Dialog>
  </section>
</template>
