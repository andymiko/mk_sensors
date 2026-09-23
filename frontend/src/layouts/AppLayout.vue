<script setup>
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import Avatar from "primevue/avatar";
import Button from "primevue/button";
import BrandMark from "../components/BrandMark.vue";
import { useAuthStore } from "../stores/auth";
import { useAssignmentsStore } from "../stores/assignments";
import { useThemeStore } from "../stores/theme";

const auth = useAuthStore();
const assignments = useAssignmentsStore();
const theme = useThemeStore();
const route = useRoute();
const router = useRouter();
const mobileOpen = ref(false);
const items = computed(() =>
  [
    { label: "Дашборд", icon: "pi-home", name: "dashboard" },
    { label: "Карта", icon: "pi-map", name: "map", permission: "map.view" },
    { label: "Объекты контроля", icon: "pi-building", name: "objects", permission: "object.view" },
    { label: "Текущие показания", icon: "pi-wave-pulse", name: "events", permission: "event.view" },
    { label: "Назначения", icon: "pi-clipboard", name: "assignments", permission: "assignment.view" },
    { label: "Подразделения", icon: "pi-sitemap", name: "divisions", permission: "access.manage" },
    { label: "Журнал прогнозов", icon: "pi-chart-line", name: "forecasts", permission: "forecast.view" },
    { label: "Тестирование прогноза", icon: "pi-sparkles", name: "forecast-test", roles: ["admin", "manager"] },
    {
      label: "Администрирование",
      icon: "pi-shield",
      name: "admin",
      roles: ["admin"],
    },
  ].filter(
    (item) =>
      (!item.permission || auth.hasPermission(item.permission)) &&
      (!item.roles || item.roles.some((role) => auth.roleCodes.includes(role))),
  ),
);
const initials = computed(() =>
  (auth.user?.name || "П")
    .split(" ")
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase(),
);
const pendingAssignments = computed(() => assignments.items.filter(
  (item) => item.status === "pending" && item.technician_id === auth.user?.id,
).length);
function logout() {
  auth.logout();
  router.push({ name: "login" });
}
onMounted(() => {
  if (auth.roleCodes.includes("technician") && auth.hasPermission("assignment.view"))
    assignments.load().catch(() => {});
});
</script>

<template>
  <div class="app-shell">
    <button
      v-if="mobileOpen"
      class="sidebar-backdrop"
      aria-label="Закрыть меню"
      @click="mobileOpen = false"
    />
    <aside :class="['sidebar', { open: mobileOpen }]">
      <div class="sidebar-brand">
        <BrandMark />
        <div>
          <strong>МОСКОЛЛЕКТОР</strong><span>Сервис предиктивной аналитики</span>
        </div>
      </div>
      <nav class="side-nav" aria-label="Основная навигация">
        <RouterLink
          v-for="item in items"
          :key="item.name"
          :to="{ name: item.name }"
          :class="['nav-link', { active: route.name === item.name }]"
          @click="mobileOpen = false"
          ><i :class="['pi', item.icon]" /><span class="nav-link-label">{{
            item.label
          }}<strong v-if="item.name === 'assignments' && pendingAssignments" class="nav-badge">{{ pendingAssignments }}</strong></span></RouterLink
        >
      </nav>
      <RouterLink :to="{ name: 'profile' }" class="user-card"
        ><Avatar :label="initials" shape="circle" />
        <div>
          <strong>{{ auth.user?.name }}</strong
          ><span>{{ auth.user?.email }}</span>
        </div></RouterLink
      >
    </aside>
    <section class="main-area">
      <header class="topbar">
        <Button
          icon="pi pi-bars"
          text
          rounded
          class="mobile-menu"
          aria-label="Открыть меню"
          @click="mobileOpen = true"
        />
        <div>
          <span class="topbar-kicker">Прогноз отказов насосов и вентиляции</span
          ><strong>{{ route.meta.title }}</strong>
        </div>
        <div class="topbar-actions">
          <Button
            :icon="theme.dark ? 'pi pi-sun' : 'pi pi-moon'"
            text
            rounded
            :aria-label="theme.label"
            @click="theme.toggle"
          />
          <Button
            icon="pi pi-sign-out"
            text
            rounded
            severity="secondary"
            aria-label="Выйти"
            @click="logout"
          />
        </div>
      </header>
      <main class="page-content"><RouterView :key="route.fullPath" /></main>
    </section>
  </div>
</template>
