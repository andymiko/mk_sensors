import { ref } from "vue";
import { defineStore } from "pinia";
import { apiRequest } from "../services/api";

export const useMonitoringStore = defineStore("monitoring", () => {
  const objects = ref([]);
  const mapObjects = ref([]);
  const objectTotal = ref(0);
  const channels = ref([]);
  const events = ref([]);
  const eventTotal = ref(0);
  const eventPage = ref(1);
  const eventPageSize = ref(20);
  const loadingObjects = ref(false);
  const loadingEvents = ref(false);
  const error = ref("");

  async function loadObjects({
    sortBy = "id",
    sortOrder = "asc",
    search = "",
    districtId = null,
  } = {}) {
    loadingObjects.value = true;
    error.value = "";
    try {
      const query = new URLSearchParams({
        page_size: "100",
        sort_by: sortBy,
        sort_order: sortOrder,
      });
      if (search.trim()) query.set("search", search.trim());
      if (districtId) query.set("district_id", districtId);
      const result = await apiRequest(`/objects?${query}`);
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

  async function loadMapObjects() {
    loadingObjects.value = true;
    error.value = "";
    try {
      mapObjects.value = await apiRequest("/objects/map");
      objectTotal.value = mapObjects.value.length;
    } catch (requestError) {
      error.value = requestError.message;
      throw requestError;
    } finally {
      loadingObjects.value = false;
    }
  }

  async function loadObjectDetails(objectId) {
    return apiRequest(`/objects/${objectId}/details`);
  }

  async function updateObject(objectId, payload) {
    const updated = await apiRequest(`/objects/${objectId}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    });
    objects.value = objects.value.map((item) =>
      item.id === objectId ? updated : item,
    );
    return updated;
  }

  async function loadEvents(filters = {}, { page = 1, pageSize = eventPageSize.value } = {}) {
    loadingEvents.value = true;
    error.value = "";
    try {
      const query = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
      for (const [key, value] of Object.entries(filters)) {
        if (value !== null && value !== undefined && value !== "")
          query.set(key, value);
      }
      const result = await apiRequest(`/events?${query}`);
      events.value = result.items;
      eventTotal.value = result.total;
      eventPage.value = result.page;
      eventPageSize.value = result.page_size;
    } catch (requestError) {
      error.value = requestError.message;
      throw requestError;
    } finally {
      loadingEvents.value = false;
    }
  }

  return {
    objects,
    mapObjects,
    objectTotal,
    channels,
    events,
    eventTotal,
    eventPage,
    eventPageSize,
    loadingObjects,
    loadingEvents,
    error,
    loadObjects,
    loadChannels,
    loadMapObjects,
    loadObjectDetails,
    updateObject,
    loadEvents,
  };
});
