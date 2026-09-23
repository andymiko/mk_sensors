import { ref } from "vue";
import { acceptHMRUpdate, defineStore } from "pinia";
import { apiRequest } from "../services/api";

export const useAssignmentsStore = defineStore("assignments", () => {
  const items = ref([]);
  const technicians = ref([]);
  const channels = ref([]);
  const loading = ref(false);
  const saving = ref(false);
  const error = ref("");

  async function load() {
    loading.value = true;
    error.value = "";
    try {
      items.value = await apiRequest("/assignments");
    } catch (requestError) {
      error.value = requestError.message;
      throw requestError;
    } finally {
      loading.value = false;
    }
  }

  async function loadOptions(objectId) {
    technicians.value = [];
    channels.value = [];
    if (!objectId) return;
    const [availableTechnicians, availableChannels] = await Promise.all([
      apiRequest(`/assignments/technicians?object_id=${objectId}`),
      apiRequest(`/channels?object_id=${objectId}&page_size=100`),
    ]);
    technicians.value = availableTechnicians;
    channels.value = availableChannels.items;
  }

  function clearOptions() {
    technicians.value = [];
    channels.value = [];
  }

  async function create(payload) {
    saving.value = true;
    error.value = "";
    try {
      const created = await apiRequest("/assignments", {
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

  async function complete(assignmentId) {
    saving.value = true;
    error.value = "";
    try {
      const updated = await apiRequest(`/assignments/${assignmentId}/complete`, {
        method: "PATCH",
      });
      items.value = items.value.map((item) => item.id === assignmentId ? updated : item);
      return updated;
    } catch (requestError) {
      error.value = requestError.message;
      throw requestError;
    } finally {
      saving.value = false;
    }
  }

  async function completeItem(assignmentId, channelId) {
    saving.value = true;
    error.value = "";
    try {
      const updated = await apiRequest(
        `/assignments/${assignmentId}/items/${channelId}/complete`,
        { method: "PATCH" },
      );
      items.value = items.value.map((item) => item.id === assignmentId ? updated : item);
      return updated;
    } catch (requestError) {
      error.value = requestError.message;
      throw requestError;
    } finally {
      saving.value = false;
    }
  }

  return { items, technicians, channels, loading, saving, error, load, loadOptions, clearOptions, create, complete, completeItem };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useAssignmentsStore, import.meta.hot));
}
