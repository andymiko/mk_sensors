<script setup>
import BrandMark from "../components/BrandMark.vue";
</script>

<template>
  <main class="auth-shell">
    <section class="auth-hero">
      <div class="hero-copy">
        <BrandMark />
        <span class="eyebrow">BASE PROJECT</span>
        <h1>Надёжная основа для нового продукта.</h1>
        <p>
          Пользователи, доступы и файловое пространство уже готовы — добавьте
          предметную область своего проекта.
        </p>
      </div>
      <div class="sound-grid" aria-hidden="true">
        <span
          v-for="index in 28"
          :key="index"
          :style="{ height: `${18 + ((index * 17) % 70)}%` }"
        />
      </div>
    </section>
    <section class="auth-form-panel"><slot /></section>
  </main>
</template>
