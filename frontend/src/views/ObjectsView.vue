<script setup>
import { onMounted } from "vue";
import Column from "primevue/column";
import DataTable from "primevue/datatable";
import Message from "primevue/message";
import { useMonitoringStore } from "../stores/monitoring";

const monitoring = useMonitoringStore();
onMounted(() => monitoring.loadObjects());

function sort(event) {
  monitoring.loadObjects({
    sortBy: event.sortField || "id",
    sortOrder: event.sortOrder === -1 ? "desc" : "asc",
  });
}
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
        <Column field="id" header="ID" sortable />
        <Column field="dispatch_name" header="Название" sortable />
        <Column field="object_type" header="Тип" sortable />
        <Column field="hierarchy_level" header="Уровень" sortable />
        <Column field="district_id" header="Район">
          <template #body="{ data }">{{ data.district_id || "Не назначен" }}</template>
        </Column>
        <Column header="Координаты">
          <template #body="{ data }">
            <span v-if="data.longitude != null && data.latitude != null">
              {{ data.latitude.toFixed(5) }}, {{ data.longitude.toFixed(5) }}
            </span>
            <span v-else class="muted-text">Нет данных</span>
          </template>
        </Column>
        <template #empty>Доступные объекты не найдены.</template>
      </DataTable>
    </div>
  </section>
</template>
