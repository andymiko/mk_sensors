import { ref } from "vue";
import { defineStore } from "pinia";
import { apiRequest } from "../services/api";

export const useForecastsStore = defineStore("forecasts", () => {
  const items = ref([]);
  const channels = ref([]);
  const loading = ref(false);
  const saving = ref(false);
  const error = ref("");

  async function load() {
    loading.value = true;
    error.value = "";
    try {
      items.value = await apiRequest("/forecasts");
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
