<script setup>
import { computed, onMounted, ref } from "vue";
import Button from "primevue/button";
import Column from "primevue/column";
import DataTable from "primevue/datatable";
import Message from "primevue/message";
import Select from "primevue/select";
import Tag from "primevue/tag";
import { apiRequest } from "../services/api";

const objects = ref([]);
const districts = ref([]);
const divisions = ref([]);
const loading = ref(false);
const savingId = ref(null);
const error = ref("");
const success = ref("");
const selectedDistricts = ref({});

const divisionNames = computed(() =>
  Object.fromEntries(divisions.value.map((item) => [item.id, item.name])),
);
const districtOptions = computed(() =>
  districts.value.map((item) => ({ label: item.name, value: item.id })),
);

async function load() {
  loading.value = true;
  error.value = "";
  try {
    const [objectPage, districtItems, divisionItems] = await Promise.all([
      apiRequest("/objects?page_size=100&sort_by=dispatch_name"),
      apiRequest("/admin/districts"),
      apiRequest("/admin/divisions"),
    ]);
    objects.value = objectPage.items;
    districts.value = districtItems;
    divisions.value = divisionItems;
    selectedDistricts.value = Object.fromEntries(
      objectPage.items.map((item) => [item.id, item.district_id]),
    );
  } catch (requestError) {
    error.value = requestError.message;
  } finally {
    loading.value = false;
  }
}

function districtFor(id) {
  return districts.value.find((item) => item.id === id);
}

async function save(object) {
  savingId.value = object.id;
  error.value = "";
  success.value = "";
  try {
    const updated = await apiRequest(`/admin/objects/${object.id}/district`, {
      method: "PUT",
      body: JSON.stringify({ district_id: selectedDistricts.value[object.id] || null }),
    });
    objects.value = objects.value.map((item) =>
      item.id === updated.id ? updated : item,
    );
    success.value = `Назначение объекта «${object.dispatch_name}» сохранено.`;
  } catch (requestError) {
    error.value = requestError.message;
  } finally {
    savingId.value = null;
  }
}

onMounted(load);
</script>

<template>
  <section class="page-stack">
    <div class="page-title">
      <span class="eyebrow">ДОСТУП К ОБЪЕКТАМ</span>
      <h1>Назначения</h1>
      <p>Район связывает объект с эксплуатационными и диспетчерскими подразделениями.</p>
    </div>
    <Message v-if="error" severity="error">{{ error }}</Message>
    <Message v-if="success" severity="success" closable @close="success = ''">{{ success }}</Message>
    <div class="section-card table-card">
      <DataTable :value="objects" :loading="loading" striped-rows responsive-layout="scroll">
        <Column field="id" header="ID" />
        <Column field="dispatch_name" header="Объект" />
        <Column header="Район">
          <template #body="{ data }">
            <Select
              v-model="selectedDistricts[data.id]"
              :options="districtOptions"
              option-label="label"
              option-value="value"
              placeholder="Выберите район"
              show-clear
              filter
              class="assignment-select"
            />
          </template>
        </Column>
        <Column header="Подразделения">
          <template #body="{ data }">
            <div class="tag-wrap">
              <Tag
                v-for="divisionId in districtFor(selectedDistricts[data.id])?.division_ids || []"
                :key="divisionId"
                :value="divisionNames[divisionId] || divisionId"
                severity="secondary"
              />
              <span v-if="!districtFor(selectedDistricts[data.id])" class="muted-text">Не назначены</span>
            </div>
          </template>
        </Column>
        <Column header="">
          <template #body="{ data }">
            <Button
              label="Сохранить"
              icon="pi pi-check"
              size="small"
              :loading="savingId === data.id"
              :disabled="selectedDistricts[data.id] === data.district_id"
              @click="save(data)"
            />
          </template>
        </Column>
        <template #empty>Объекты не найдены.</template>
      </DataTable>
    </div>
  </section>
</template>
