<script setup>
import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import { useToast } from "primevue/usetoast";
import Button from "primevue/button";
import Message from "primevue/message";
import ProgressSpinner from "primevue/progressspinner";
import { useFilesStore } from "../stores/files";

const files = useFilesStore();
const router = useRouter();
const toast = useToast();
const file = ref(null);
const dragging = ref(false);
const error = ref("");
const formattedSize = computed(() =>
  file.value ? `${(file.value.size / 1024 / 1024).toFixed(1)} МБ` : "",
);
function selectFile(selected) {
  error.value = "";
  if (selected) file.value = selected;
}
function onDrop(event) {
  dragging.value = false;
  selectFile(event.dataTransfer.files[0]);
}
async function submit() {
  if (!file.value) return;
  try {
    await files.upload(file.value);
    toast.add({ severity: "success", summary: "Файл загружен", life: 2500 });
    router.push({ name: "files" });
  } catch (uploadError) {
    error.value = uploadError.message;
  }
}
</script>

<template>
  <section class="page-stack narrow-page">
    <div class="page-title">
      <span class="eyebrow">НОВЫЙ ФАЙЛ</span>
      <h1>Загрузка файла</h1>
      <p>
        Файл будет сохранён в защищённом хранилище и появится в вашей истории.
      </p>
    </div>
    <Message v-if="error" severity="error" :closable="false">{{
      error
    }}</Message>
    <div
      :class="['upload-zone', { dragging, selected: file }]"
      @dragover.prevent="dragging = true"
      @dragleave.prevent="dragging = false"
      @drop.prevent="onDrop"
    >
      <input
        id="project-file"
        type="file"
        hidden
        @change="selectFile($event.target.files[0])"
      />
      <template v-if="!file"
        ><span class="upload-icon"><i class="pi pi-cloud-upload" /></span>
        <h2>Перетащите файл сюда</h2>
        <p>или выберите его на компьютере</p>
        <label for="project-file" class="p-button p-component p-button-outlined"
          ><i class="pi pi-folder-open" /><span>Выбрать файл</span></label
        ></template
      >
      <template v-else
        ><span class="upload-icon ready"><i class="pi pi-file-check" /></span>
        <h2>{{ file.name }}</h2>
        <p>{{ formattedSize }}</p>
        <Button label="Убрать" severity="danger" text @click="file = null"
      /></template>
    </div>
    <Button
      label="Загрузить"
      icon="pi pi-upload"
      size="large"
      :disabled="!file"
      :loading="files.uploading"
      @click="submit"
    />
    <div v-if="files.uploading" class="upload-overlay">
      <ProgressSpinner /><strong>Загружаем файл…</strong>
    </div>
  </section>
</template>
