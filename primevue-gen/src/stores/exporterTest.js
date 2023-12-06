import { computed, ref } from "vue";
import { defineStore } from "pinia";

export const useExporterTestStore = defineStore("exporterTest", () => {
  const results = ref({});
  const visible = computed(() => Object.keys(results.value).length > 0);

  // Results control
  function addResult(url, statusCode) {
    results.value[url] = statusCode;
  }

  function setResults(newResults) {
    results.value = { ...newResults };
  }

  return { results, addResult, setResults, visible };
});
