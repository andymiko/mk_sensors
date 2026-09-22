<script setup>
import { computed } from "vue";

import Avatar from "primevue/avatar";
import Tag from "primevue/tag";

import { useAuthStore } from "../stores/auth";

import { useAdminStore } from "../stores/admin";

const admin = useAdminStore();

const auth = useAuthStore();
const initials = computed(() =>
  (auth.user?.name || "П")
    .split(" ")
    .map((part) => part[0])
    .slice(0, 2)
    .join("")
    .toUpperCase(),
);
</script>

<template>
  <section class="page-stack narrow-page">
    <div class="page-title">
      <span class="eyebrow">АККАУНТ</span>
      <h1>Профиль</h1>
      <p>Данные пользователя и доступные возможности.</p>
    </div>

    <div class="section-card profile-card">
      <Avatar :label="initials" size="xlarge" shape="circle" />
      <div>
        <h2>{{ auth.user?.name }}</h2>
        <p>{{ auth.user?.email }}</p>
        <div class="tag-list">
          <Tag
            v-for="role in auth.roleCodes"
            :key="role"
            :value="role"
            severity="info"
            rounded
          />
        </div>
      </div>
    </div>

    <div class="section-card">
      <div class="section-heading">
        <div>
          <h2>Права доступа</h2>
          <p>Назначаются через роли пользователя</p>
        </div>
      </div>

      <div class="permission-grid">
        <div v-for="permission in auth.permissions" :key="permission.id">
          <i class="pi pi-check-circle" />
          <span class="permission-details">
            <strong>{{ permission.name }}</strong>
            <code>{{ permission.code }}</code>
          </span>
        </div>
        <p v-if="!auth.permissionCodes.length">
          Права доступа пока не назначены.
        </p>
      </div>
    </div>
  </section>
</template>
