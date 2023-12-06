<script setup>
import { computed, onMounted, ref } from "vue";

import { localize, percent } from "../utils/filters.js";

const props = defineProps({
  href: {
    type: String,
    default: "",
  },
  max: {
    type: Number,
    default: 1, // Avoid division by 0
  },
  query: {
    type: String,
    default: "",
  },
});

const count = ref(0);
const visible = ref(false);

const load = computed(() => count.value / props.max);

const classes = computed(() => {
  if (load.value > 0.9) return "label label-danger";
  if (load.value > 0.7) return "label label-warning";
  if (load.value > 0.5) return "label label-info";
  if (count.value == 0) return "label label-default";
  return "label label-success";
});

onMounted(() => {
  const url = new URL(props.href);
  url.search = new URLSearchParams({ query: props.query });
  fetch(url)
    .then((response) => response.json())
    .then((result) => Number.parseInt(result.data.result[0].value[1]))
    .then((result) => (count.value = result))
    .finally(() => (visible.value = true));
});
</script>

<template>
  <span
    v-show="visible"
    :title="percent(load)"
    :class="classes"
  >
    <slot /> {{ localize(count) }}
  </span>
</template>
