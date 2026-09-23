<script setup>
import { ref } from "vue";
import { useToast } from "primevue/usetoast";
import Button from "primevue/button";
import { downloadReport } from "../services/reports";

const props = defineProps({ dataset: { type: String, required: true }, params: { type: Object, default: () => ({}) } });
const loading = ref(null);
const toast = useToast();

async function download(format) {
  loading.value = format;
  try {
    await downloadReport(props.dataset, format, props.params);
  } catch (error) {
    toast.add({ severity: "error", summary: "Отчёт не сформирован", detail: error.message, life: 5000 });
  } finally {
    loading.value = null;
  }
}
</script>

<template>
  <div class="report-buttons" aria-label="Экспорт отчёта">
    <Button label="CSV" icon="pi pi-download" size="small" severity="secondary" outlined :loading="loading === 'csv'" @click="download('csv')" />
    <Button label="XLSX" icon="pi pi-file-excel" size="small" severity="success" outlined :loading="loading === 'xlsx'" @click="download('xlsx')" />
    <Button label="PDF" icon="pi pi-file-pdf" size="small" severity="danger" outlined :loading="loading === 'pdf'" @click="download('pdf')" />
  </div>
</template>
