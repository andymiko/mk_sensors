import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "../stores/auth";

const routes = [
  {
    path: "/login",
    name: "login",
    component: () => import("../views/LoginView.vue"),
    meta: { guest: true },
  },
  {
    path: "/register",
    name: "register",
    component: () => import("../views/RegisterView.vue"),
    meta: { guest: true },
  },
  {
    path: "/",
    component: () => import("../layouts/AppLayout.vue"),
    meta: { auth: true },
    children: [
      {
        path: "",
        name: "dashboard",
        component: () => import("../views/DashboardView.vue"),
        meta: { title: "Дашборд" },
      },
      {
        path: "map",
        name: "map",
        component: () => import("../views/MapView.vue"),
        meta: { permission: "map.view", title: "Карта" },
      },
      {
        path: "objects",
        name: "objects",
        component: () => import("../views/ObjectsView.vue"),
        meta: { permission: "object.view", title: "Объекты контроля" },
      },
      {
        path: "events",
        name: "events",
        component: () => import("../views/EventsView.vue"),
        meta: { permission: "event.view", title: "Текущие показания" },
      },
      {
        path: "forecasts",
        name: "forecasts",
        component: () => import("../views/PlaceholderView.vue"),
        props: { title: "Журнал прогнозов", eyebrow: "АНАЛИТИКА", icon: "pi-chart-line" },
        meta: { permission: "forecast.view", title: "Журнал прогнозов" },
      },
      {
        path: "notifications",
        name: "notifications",
        component: () => import("../views/PlaceholderView.vue"),
        props: { title: "Уведомления", eyebrow: "СОБЫТИЯ", icon: "pi-bell" },
        meta: { permission: "notification.view", title: "Уведомления" },
      },
      {
        path: "assignments",
        name: "assignments",
        component: () => import("../views/AssignmentsView.vue"),
        meta: { permission: "assignment.view", title: "Назначения" },
      },
      {
        path: "divisions",
        name: "divisions",
        component: () => import("../views/DivisionsView.vue"),
        meta: { permission: "access.manage", title: "Подразделения" },
      },
      {
        path: "admin/:section?",
        name: "admin",
        component: () => import("../views/AdminView.vue"),
        meta: { roles: ["admin"], title: "Администрирование" },
      },
      {
        path: "profile",
        name: "profile",
        component: () => import("../views/ProfileView.vue"),
        meta: { title: "Профиль" },
      },
    ],
  },
  { path: "/:pathMatch(.*)*", redirect: "/" },
];

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
});

router.beforeEach(async (to) => {
  const auth = useAuthStore();
  if (auth.token && !auth.user) {
    try {
      await auth.fetchMe();
    } catch {
      return { name: "login" };
    }
  }
  if (to.meta.auth && !auth.isAuthenticated)
    return { name: "login", query: { redirect: to.fullPath } };
  if (to.meta.guest && auth.isAuthenticated) return { name: "dashboard" };
  if (to.meta.permission && !auth.hasPermission(to.meta.permission))
    return { name: "dashboard" };
  if (
    to.meta.roles &&
    !to.meta.roles.some((role) => auth.roleCodes.includes(role))
  )
    return { name: "dashboard" };
});

export default router;
