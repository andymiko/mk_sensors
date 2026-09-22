import { ref } from "vue";
import { defineStore } from "pinia";
import { apiRequest, downloadFile } from "../services/api";

export const useFilesStore = defineStore("files", () => {
  const items = ref([]);
  const total = ref(0);
  const loading = ref(false);
  const uploading = ref(false);

  async function load(search = "") {
    loading.value = true;
    try {
      const query = search ? `?search=${encodeURIComponent(search)}` : "";
      const page = await apiRequest(`/files${query}`);
      items.value = page.items;
      total.value = page.total;
    } finally {
      loading.value = false;
    }
  }

  async function upload(file) {
    uploading.value = true;
    try {
      const body = new FormData();
      body.append("upload", file);
      const created = await apiRequest("/files", { method: "POST", body });
      items.value.unshift(created);
      total.value += 1;
      return created;
    } finally {
      uploading.value = false;
    }
  }

  async function remove(file) {
    await apiRequest(`/files/${file.id}`, { method: "DELETE" });
    items.value = items.value.filter((item) => item.id !== file.id);
    total.value -= 1;
  }

  return {
    items,
    total,
    loading,
    uploading,
    load,
    upload,
    remove,
    download: downloadFile,
  };
});
