import { ref } from "vue";
import { defineStore } from "pinia";
import { apiRequest } from "../services/api";

export const useMonitoringStore = defineStore("monitoring", () => {
  const objects = ref([]);
  const objectTotal = ref(0);
  const channels = ref([]);
  const events = ref([]);
  const eventTotal = ref(0);
  const loadingObjects = ref(false);
  const loadingEvents = ref(false);
  const error = ref("");

  async function loadObjects({ sortBy = "id", sortOrder = "asc" } = {}) {
    loadingObjects.value = true;
    error.value = "";
    try {
      const result = await apiRequest(
        `/objects?page_size=100&sort_by=${sortBy}&sort_order=${sortOrder}`,
      );
      objects.value = result.items;
      objectTotal.value = result.total;
    } catch (requestError) {
      error.value = requestError.message;
      throw requestError;
    } finally {
      loadingObjects.value = false;
    }
  }

  async function loadChannels() {
    const result = await apiRequest("/channels?page_size=100");
    channels.value = result.items;
  }

  async function loadEvents(filters = {}) {
    loadingEvents.value = true;
    error.value = "";
    try {
      const query = new URLSearchParams({ page_size: "100" });
      for (const [key, value] of Object.entries(filters)) {
        if (value !== null && value !== undefined && value !== "")
          query.set(key, value);
      }
      const result = await apiRequest(`/events?${query}`);
      events.value = result.items;
      eventTotal.value = result.total;
    } catch (requestError) {
      error.value = requestError.message;
      throw requestError;
    } finally {
      loadingEvents.value = false;
    }
  }

  return {
    objects,
    objectTotal,
    channels,
    events,
    eventTotal,
    loadingObjects,
    loadingEvents,
    error,
    loadObjects,
    loadChannels,
    loadEvents,
  };
});
