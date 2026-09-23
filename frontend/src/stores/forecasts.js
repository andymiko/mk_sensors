import { ref } from "vue";
import { defineStore } from "pinia";
import { apiRequest } from "../services/api";

export const useForecastsStore = defineStore("forecasts", () => {
  const items = ref([]);
  const channels = ref([]);
  const loading = ref(false);
  const saving = ref(false);
  const error = ref("");

  async function load(filters = {}) {
    loading.value = true;
    error.value = "";
    try {
      const query = new URLSearchParams();
      for (const [key, value] of Object.entries(filters)) {
        if (value !== null && value !== undefined && value !== "") query.set(key, value);
      }
      items.value = await apiRequest(`/forecasts?${query}`);
    } catch (requestError) {
      error.value = requestError.message;
      throw requestError;
    } finally {
      loading.value = false;
    }
  }

  async function loadChannels() {
    channels.value = await apiRequest("/forecasts/channels");
  }

  async function create(payload) {
    saving.value = true;
    error.value = "";
    try {
      const created = await apiRequest("/forecasts", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      items.value = [created, ...items.value];
      return created;
    } catch (requestError) {
      error.value = requestError.message;
      throw requestError;
    } finally {
      saving.value = false;
    }
  }

  return { items, channels, loading, saving, error, load, loadChannels, create };
});
