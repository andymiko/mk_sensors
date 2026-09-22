import { computed, ref, watch } from "vue";
import { defineStore } from "pinia";

export const useThemeStore = defineStore("theme", () => {
  const stored = localStorage.getItem("baseproject_theme");
  const dark = ref(
    stored
      ? stored === "dark"
      : window.matchMedia("(prefers-color-scheme: dark)").matches,
  );
  const label = computed(() => (dark.value ? "Светлая тема" : "Тёмная тема"));

  watch(
    dark,
    (value) => {
      document.documentElement.classList.toggle("app-dark", value);
      localStorage.setItem("baseproject_theme", value ? "dark" : "light");
    },
    { immediate: true },
  );

  function toggle() {
    dark.value = !dark.value;
  }
  return { dark, label, toggle };
});
