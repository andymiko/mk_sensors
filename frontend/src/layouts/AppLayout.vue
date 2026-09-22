<script setup>
import { computed, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import Avatar from "primevue/avatar";
import Button from "primevue/button";
import BrandMark from "../components/BrandMark.vue";
import { useAuthStore } from "../stores/auth";
import { useThemeStore } from "../stores/theme";

const auth = useAuthStore();
const theme = useThemeStore();
const route = useRoute();
const router = useRouter();
const mobileOpen = ref(false);
const items = computed(() =>
  [
    { label: "Обзор", icon: "pi-home", name: "dashboard" },
    {
      label: "Загрузить файл",
      icon: "pi-cloud-upload",
      name: "upload",
      permission: "file.upload",
    },
    {
      label: "Мои файлы",
      icon: "pi-folder",
      name: "files",
      permission: "file.download",
    },
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
function logout() {
  auth.logout();
  router.push({ name: "login" });
}
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
          <strong>Base Project</strong><span>Рабочее пространство</span>
        </div>
      </div>
      <nav class="side-nav" aria-label="Основная навигация">
        <RouterLink
          v-for="item in items"
          :key="item.name"
          :to="{ name: item.name }"
          class="nav-link"
          @click="mobileOpen = false"
          ><i :class="['pi', item.icon]" /><span>{{
            item.label
          }}</span></RouterLink
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
          <span class="topbar-kicker">Рабочее пространство</span
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
      <main class="page-content"><RouterView /></main>
    </section>
  </div>
</template>
