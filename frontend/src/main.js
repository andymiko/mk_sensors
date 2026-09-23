import { createApp } from "vue";
import { createPinia } from "pinia";
import PrimeVue from "primevue/config";
import ToastService from "primevue/toastservice";
import Aura from "@primeuix/themes/aura";
import "primeicons/primeicons.css";

import App from "./App.vue";
import router from "./router";
import "./styles/main.css";

createApp(App)
  .use(createPinia())
  .use(router)
  .use(PrimeVue, {
    locale: {
      firstDayOfWeek: 1,
      dayNames: ["Воскресенье", "Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота"],
      dayNamesShort: ["Вс", "Пн", "Вт", "Ср", "Чт", "Пт", "Сб"],
      dayNamesMin: ["Вс", "Пн", "Вт", "Ср", "Чт", "Пт", "Сб"],
      monthNames: ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"],
      monthNamesShort: ["Янв", "Фев", "Мар", "Апр", "Май", "Июн", "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек"],
      today: "Сегодня",
      clear: "Очистить",
      weekHeader: "Нед",
      dateFormat: "dd.mm.yy",
    },
    theme: {
      preset: Aura,
      options: { darkModeSelector: ".app-dark" },
    },
    ripple: true,
  })
  .use(ToastService)
  .mount("#app");
