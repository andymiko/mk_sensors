<script setup>
import { onMounted, ref, watch } from "vue";
import { useToast } from "primevue/usetoast";
import Button from "primevue/button";
import Column from "primevue/column";
import DataTable from "primevue/datatable";
import InputText from "primevue/inputtext";
import EmptyState from "../components/EmptyState.vue";
import { useFilesStore } from "../stores/files";

const files = useFilesStore();
const toast = useToast();
const search = ref("");
let timer;
const size = (value) =>
  value < 1024 * 1024
    ? `${(value / 1024).toFixed(1)} КБ`
    : `${(value / 1024 / 1024).toFixed(1)} МБ`;
watch(search, () => {
  clearTimeout(timer);
  timer = setTimeout(() => files.load(search.value), 300);
});
async function remove(file) {
  if (!window.confirm(`Удалить файл «${file.original_name}»?`)) return;
  try {
    await files.remove(file);
  } catch (error) {
    toast.add({
      severity: "error",
      summary: "Ошибка удаления",
      detail: error.message,
      life: 4000,
    });
  }
}
async function download(file) {
  try {
    await files.download(file);
  } catch (error) {
    toast.add({
      severity: "error",
      summary: "Ошибка скачивания",
      detail: error.message,
      life: 4000,
    });
  }
}
onMounted(() => files.load());
</script>

<template>
  <section class="page-stack">
    <div class="page-title-row">
      <div class="page-title">
        <span class="eyebrow">ФАЙЛОВОЕ ХРАНИЛИЩЕ</span>
        <h1>История загрузок</h1>
        <p>Загруженные вами файлы доступны для скачивания и удаления.</p>
      </div>
      <RouterLink :to="{ name: 'upload' }"
        ><Button label="Загрузить файл" icon="pi pi-plus"
      /></RouterLink>
    </div>
    <div class="filter-bar">
      <span class="search-field"
        ><i class="pi pi-search" /><InputText
          v-model="search"
          placeholder="Поиск по имени"
      /></span>
    </div>
    <div class="section-card table-card">
      <DataTable
        v-if="files.items.length"
        :value="files.items"
        :loading="files.loading"
        paginator
        :rows="10"
        responsive-layout="scroll"
      >
        <Column field="original_name" header="Файл" /><Column header="Размер"
          ><template #body="{ data }">{{ size(data.size) }}</template></Column
        ><Column header="Загружен"
          ><template #body="{ data }">{{
            new Date(data.created_at * 1000).toLocaleString("ru-RU")
          }}</template></Column
        >
        <Column header=""
          ><template #body="{ data }"
            ><div class="table-actions">
              <Button
                icon="pi pi-download"
                text
                rounded
                aria-label="Скачать"
                @click="download(data)"
              /><Button
                icon="pi pi-trash"
                text
                rounded
                severity="danger"
                aria-label="Удалить"
                @click="remove(data)"
              /></div></template
        ></Column>
      </DataTable>
      <EmptyState
        v-else
        icon="pi-folder-open"
        title="Файлов пока нет"
        text="Загрузите первый файл, чтобы он появился в истории."
      />
    </div>
  </section>
</template>
