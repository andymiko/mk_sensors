<script setup>
import { onMounted } from "vue";
import Button from "primevue/button";
import { useAuthStore } from "../stores/auth";
import { useFilesStore } from "../stores/files";
const auth = useAuthStore();
const files = useFilesStore();
onMounted(() => files.load());
</script>

<template>
  <section class="page-stack">
    <div class="page-title">
      <span class="eyebrow">ОБЗОР</span>
      <h1>Здравствуйте, {{ auth.user?.name }}</h1>
      <p>Базовое рабочее пространство для нового продукта.</p>
    </div>
    <div class="stats-grid">
      <article class="stat-card">
        <i class="pi pi-folder" />
        <div>
          <span>Ваши файлы</span><strong>{{ files.total }}</strong>
        </div>
      </article>
      <article class="stat-card">
        <i class="pi pi-shield" />
        <div>
          <span>Роли</span><strong>{{ auth.roleCodes.length }}</strong>
        </div>
      </article>
    </div>
    <div class="section-card empty-dashboard">
      <h2>Быстрый старт</h2>
      <p>Загрузите файл или перейдите к истории сохранённых материалов.</p>
      <div class="inline-actions">
        <RouterLink :to="{ name: 'upload' }"
          ><Button label="Загрузить файл" icon="pi pi-upload" /></RouterLink
        ><RouterLink :to="{ name: 'files' }"
          ><Button label="Открыть историю" outlined
        /></RouterLink>
      </div>
    </div>
  </section>
</template>
