<script setup>
import EmptyState from "../components/EmptyState.vue";
defineProps({ title: String, description: String, icon: String, eyebrow: String });
</script>

<template>
  <section class="page-stack">
    <div class="page-title">
      <span class="eyebrow">{{ eyebrow }}</span>
      <h1>{{ title }}</h1>
      <p>{{ description }}</p>
    </div>
    <div class="section-card"><EmptyState :icon="icon" title="Раздел готов к наполнению" text="Данные и рабочие сценарии будут добавлены на следующем этапе." /></div>
  </section>
</template>
