<script setup>
import { reactive, ref } from "vue";
import { useRouter } from "vue-router";

import Button from "primevue/button";
import InputText from "primevue/inputtext";
import Password from "primevue/password";
import Message from "primevue/message";

import AuthLayout from "../layouts/AuthLayout.vue";

import { useAuthStore } from "../stores/auth";

const auth = useAuthStore();
const router = useRouter();
const form = reactive({
  name: "",
  email: "",
  password: "",
});

const error = ref("");
const submitting = ref(false);

const submit = async () => {
  error.value = "";
  submitting.value = true;
  try {
    await auth.register(form);
    router.push({ name: "dashboard" });
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
        <span class="eyebrow">Новый аккаунт</span>
        <h2>Регистрация</h2>
        <p>Создайте аккаунт для работы с приложением.</p>
      </div>

      <Message v-if="error" severity="error" :closable="false">{{
        error
      }}</Message>

      <form class="form-stack" @submit.prevent="submit">
        <label
          >Имя
          <InputText
            v-model.trim="form.name"
            autocomplete="name"
            placeholder="Иванов Иван"
            minlength="1"
            maxlength="200"
            required
            fluid
          />
        </label>

        <label
          >Email
          <InputText
            v-model="form.email"
            type="email"
            autocomplete="email"
            placeholder="user@example.ru"
            required
            fluid
          />
        </label>

        <label
          >Пароль
          <Password
            v-model="form.password"
            toggle-mask
            autocomplete="new-password"
            placeholder="Не менее 8 символов"
            minlength="8"
            required
            fluid
          />
        </label>

        <Button
          type="submit"
          label="Создать аккаунт"
          icon="pi pi-user-plus"
          :loading="submitting"
          fluid
        />
      </form>

      <p class="auth-switch">
        Уже зарегистрированы?
        <RouterLink to="/login">Войти</RouterLink>
      </p>
    </div>
  </AuthLayout>
</template>
