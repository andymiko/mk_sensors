<script setup>
import { computed, onMounted, ref } from "vue";
import Button from "primevue/button";
import Message from "primevue/message";
import MultiSelect from "primevue/multiselect";
import Tag from "primevue/tag";
import { apiRequest } from "../services/api";
import { useMonitoringStore } from "../stores/monitoring";

const monitoring = useMonitoringStore();
const divisions = ref([]);
const selections = ref({});
const savingId = ref(null);
const loading = ref(false);
const error = ref("");
const success = ref("");

const objectOptions = computed(() =>
  monitoring.objects.map((item) => ({
    label: item.dispatch_name,
    value: item.id,
  })),
);

async function load() {
  loading.value = true;
  error.value = "";
  try {
    const [items] = await Promise.all([
      apiRequest("/admin/divisions/details"),
      monitoring.loadObjects({ sortBy: "dispatch_name" }),
    ]);
    divisions.value = items;
    selections.value = Object.fromEntries(
      items.map((item) => [item.id, [...item.object_ids]]),
    );
  } catch (requestError) {
    error.value = requestError.message;
  } finally {
    loading.value = false;
  }
}

async function save(division) {
  savingId.value = division.id;
  error.value = "";
  success.value = "";
  try {
    const updated = await apiRequest(`/admin/divisions/${division.id}/objects`, {
      method: "PUT",
      body: JSON.stringify({ ids: selections.value[division.id] || [] }),
    });
    divisions.value = divisions.value.map((item) =>
      item.id === updated.id ? updated : item,
    );
    selections.value[division.id] = [...updated.object_ids];
    success.value = `Объекты подразделения «${division.name}» обновлены.`;
  } catch (requestError) {
    error.value = requestError.message;
  } finally {
    savingId.value = null;
  }
}

function isChanged(division) {
  const current = [...(selections.value[division.id] || [])].sort();
  const saved = [...division.object_ids].sort();
  return JSON.stringify(current) !== JSON.stringify(saved);
}

onMounted(load);
</script>

<template>
  <section class="page-stack">
    <div class="page-title">
      <span class="eyebrow">СТРУКТУРА ДОСТУПА</span>
      <h1>Подразделения</h1>
      <p>Объекты и сотрудники, закреплённые за подразделениями.</p>
    </div>
    <Message v-if="error" severity="error">{{ error }}</Message>
    <Message v-if="success" severity="success" closable @close="success = ''">{{ success }}</Message>
    <div v-if="loading" class="section-card map-loading">Загрузка подразделений…</div>
    <div v-else class="division-grid">
      <article v-for="division in divisions" :key="division.id" class="section-card division-card">
        <div class="section-heading-inline">
          <div><h2>{{ division.name }}</h2><span class="muted-text">{{ division.code }}</span></div>
          <Tag :value="division.object_ids.length + ' объектов'" severity="secondary" />
        </div>
        <label class="division-field">
          Закреплённые объекты
          <MultiSelect
            v-model="selections[division.id]"
            :options="objectOptions"
            option-label="label"
            option-value="value"
            filter
            display="chip"
            :max-selected-labels="3"
            selected-items-label="{0} объектов выбрано"
            placeholder="Объекты не назначены"
          />
        </label>
        <div>
          <h3>Сотрудники</h3>
          <div class="member-list">
            <div v-for="user in division.users" :key="user.id" class="member-row">
              <i class="pi pi-user" />
              <div><strong>{{ user.name }}</strong><span>{{ user.email }}</span></div>
            </div>
            <span v-if="!division.users.length" class="muted-text">Сотрудники не назначены</span>
          </div>
        </div>
        <Button
          label="Сохранить объекты"
          icon="pi pi-check"
          :loading="savingId === division.id"
          :disabled="!isChanged(division)"
          @click="save(division)"
        />
      </article>
    </div>
  </section>
</template>
