<script setup>
defineProps({
  icon: {
    type: String,
    default: "pi-inbox",
  },

  title: {
    type: String,
    default: "pi-inbox",
  },

  text: {
    type: String,
    default: "pi-inbox",
  },
});
</script>

<template>
  <div class="empty-state">
    <i :class="['pi', icon]" />
    <h3>{{ title }}</h3>
    <p>{{ text }}</p>
    <slot />
  </div>
</template>
