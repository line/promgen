<script setup>
defineProps({
  heading: {
    type: String,
    default: "",
  },
});
</script>

<template>
  <div class="panel">
    <div class="panel-heading">{{ heading }}</div>
    <div class="panel-body"><slot /></div>
  </div>
</template>
