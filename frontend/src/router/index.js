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
        meta: { title: "Обзор" },
      },
      {
        path: "upload",
        name: "upload",
        component: () => import("../views/UploadView.vue"),
        meta: { permission: "file.upload", title: "Загрузка файла" },
      },
      {
        path: "files",
        name: "files",
        component: () => import("../views/FilesView.vue"),
        meta: { permission: "file.download", title: "История файлов" },
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
