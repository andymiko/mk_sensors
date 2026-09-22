<script setup>
import { computed } from "vue";

import Tag from "primevue/tag";

const props = defineProps({
  status: {
    type: String,
    required: true,
  },
});

const labels = {
  queued: "В очереди",
  processing: "Обрабатывается",
  done: "Готов",
  error: "Ошибка",
};

const severities = {
  queued: "secondary",
  processing: "info",
  done: "success",
  error: "danger",
};

const label = computed(() => labels[props.status] || props.status);

const severity = computed(() => severities[props.status] || "secondary");
</script>

<template>
  <Tag :value="label" :severity="severity" rounded />
</template>
