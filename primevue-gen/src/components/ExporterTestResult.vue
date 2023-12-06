<script setup>
import { useExporterTestStore } from "../stores/exporterTest.js";

const store = useExporterTestStore();
</script>

<template>
  <bootstrap-panel
    v-if="store.visible"
    class="panel-info"
    heading="Results"
  >
    <table class="table">
      <tr
        v-for="(val, key, index) in store.results"
        :key="index"
      >
        <td>{{ key }}</td>
        <td>{{ val }}</td>
      </tr>
    </table>
  </bootstrap-panel>
</template>
