import { computed, ref } from "vue";
import { defineStore } from "pinia";
import { apiRequest } from "../services/api";

export const useAuthStore = defineStore("auth", () => {
  const token = ref(localStorage.getItem("baseproject_token"));
  const user = ref(null);
  const loading = ref(false);

  const isAuthenticated = computed(() => Boolean(token.value && user.value));
  const roleCodes = computed(() => user.value?.role_codes || []);
  const permissionCodes = computed(() => user.value?.permission_codes || []);
  const isAdmin = computed(() => roleCodes.value.includes("admin"));

  function setToken(value) {
    token.value = value;
    if (value) localStorage.setItem("baseproject_token", value);
    else localStorage.removeItem("baseproject_token");
  }

  async function login(credentials) {
    const result = await apiRequest("/login", {
      method: "POST",
      body: JSON.stringify(credentials),
    });
    setToken(result.access_token);
    await fetchMe();
  }

  async function register(payload) {
    await apiRequest("/register", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    await login({ email: payload.email, password: payload.password });
  }

  async function fetchMe() {
    if (!token.value) return null;
    loading.value = true;
    try {
      user.value = await apiRequest("/me");
      return user.value;
    } catch (error) {
      if (error.status === 401) logout();
      throw error;
    } finally {
      loading.value = false;
    }
  }

  function logout() {
    setToken(null);
    user.value = null;
  }

  function hasPermission(code) {
    return isAdmin.value || permissionCodes.value.includes(code);
  }

  return {
    token,
    user,
    loading,
    isAuthenticated,
    roleCodes,
    permissionCodes,
    isAdmin,
    login,
    register,
    fetchMe,
    logout,
    hasPermission,
  };
});
