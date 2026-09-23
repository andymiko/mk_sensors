import { ref } from "vue";
import { acceptHMRUpdate, defineStore } from "pinia";
import { apiRequest } from "../services/api";

export const useAdminStore = defineStore("admin", () => {
  const users = ref([]);
  const roles = ref([]);
  const permissions = ref([]);
  const divisions = ref([]);
  const loading = ref(false);
  async function loadCatalog() {
    [roles.value, permissions.value] = await Promise.all([
      apiRequest("/admin/roles"),
      apiRequest("/admin/permissions"),
    ]);
  }
  async function loadAll() {
    loading.value = true;
    try {
      await Promise.all([
        loadCatalog(),
        apiRequest("/admin/users").then((data) => {
          users.value = data;
        }),
        apiRequest("/admin/divisions").then((data) => {
          divisions.value = data;
        }),
      ]);
    } finally {
      loading.value = false;
    }
  }
  async function setUserStatus(user, isActive) {
    const updated = await apiRequest(`/admin/users/${user.id}/status`, {
      method: "PATCH",
      body: JSON.stringify({ is_active: isActive }),
    });
    users.value = users.value.map((item) =>
      item.id === updated.id ? updated : item,
    );
  }
  async function updateUser(user, payload) {
    const updated = await apiRequest(`/admin/users/${user.id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
    users.value = users.value.map((item) =>
      item.id === updated.id ? updated : item,
    );
    return updated;
  }
  async function deleteUser(user) {
    await apiRequest(`/admin/users/${user.id}`, { method: "DELETE" });
    users.value = users.value.filter((item) => item.id !== user.id);
  }
  async function setUserRoles(user, roleIds) {
    const updated = await apiRequest(`/admin/users/${user.id}/roles`, {
      method: "PUT",
      body: JSON.stringify({ role_ids: roleIds }),
    });
    users.value = users.value.map((item) =>
      item.id === updated.id ? updated : item,
    );
  }
  async function setUserDivisions(user, divisionIds) {
    const updated = await apiRequest(`/admin/users/${user.id}/divisions`, {
      method: "PUT",
      body: JSON.stringify({ division_ids: divisionIds }),
    });
    users.value = users.value.map((item) =>
      item.id === updated.id ? updated : item,
    );
  }
  async function setRolePermissions(role, permissionIds) {
    await apiRequest(`/admin/roles/${role.id}/permissions`, {
      method: "PUT",
      body: JSON.stringify({ permission_ids: permissionIds }),
    });
    await loadCatalog();
  }
  async function createRole(payload) {
    await apiRequest("/admin/roles", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    await loadCatalog();
  }
  async function createPermission(payload) {
    await apiRequest("/admin/permissions", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    await loadCatalog();
  }
  return {
    users,
    roles,
    permissions,
    divisions,
    loading,
    loadAll,
    updateUser,
    deleteUser,
    setUserStatus,
    setUserRoles,
    setUserDivisions,
    setRolePermissions,
    createRole,
    createPermission,
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useAdminStore, import.meta.hot));
}
