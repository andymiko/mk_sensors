<script setup>
import BrandMark from "../components/BrandMark.vue";
</script>

<template>
  <main class="auth-shell">
    <section class="auth-hero">
      <div class="hero-copy">
        <BrandMark />
        <span class="eyebrow">МОСКОЛЛЕКТОР</span>
        <h1>Сервис предиктивной аналитики</h1>
        <p>
          Надежная инфраструктура сегодня - без аварий завтра.
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
