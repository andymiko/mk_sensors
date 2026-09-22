<script setup>
import { reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import Button from "primevue/button";
import InputText from "primevue/inputtext";
import Password from "primevue/password";
import Message from "primevue/message";

import AuthLayout from "../layouts/AuthLayout.vue";

import { useAuthStore } from "../stores/auth";

const auth = useAuthStore();
const router = useRouter();
const route = useRoute();

const form = reactive({
  email: "",
  password: "",
});

const error = ref("");
const submitting = ref(false);

const submit = async () => {
  error.value = "";
  submitting.value = true;

  try {
    await auth.login(form);
    router.push(route.query.redirect || { name: "dashboard" });
  } catch (err) {
    error.value = err.message;
  } finally {
    submitting.value = false;
  }
};
</script>

<template>
  <AuthLayout>
    <div class="auth-card">
      <div class="auth-heading">
        <span class="eyebrow">С возвращением</span>
        <h2>Вход в систему</h2>
        <p>Продолжите работу в своём пространстве.</p>
      </div>

      <Message v-if="error" severity="error" :closable="false">{{
        error
      }}</Message>

      <form class="form-stack" @submit.prevent="submit">
        <label
          >Email
          <InputText
            v-model="form.email"
            type="email"
            autocomplete="email"
            placeholder="IvanovII@mos.ru"
            required
            fluid
          />
        </label>

        <label
          >Пароль
          <Password
            v-model="form.password"
            :feedback="false"
            toggle-mask
            autocomplete="current-password"
            placeholder="Не менее 8 символов"
            required
            fluid
          />
        </label>

        <Button
          type="submit"
          label="Войти"
          icon="pi pi-arrow-right"
          icon-pos="right"
          :loading="submitting"
          fluid
        />
      </form>

      <p class="auth-switch">
        Ещё нет аккаунта?
        <RouterLink to="/register">Зарегистрироваться</RouterLink>
      </p>
    </div>
  </AuthLayout>
</template>
