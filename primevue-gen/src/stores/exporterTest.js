import { ref } from "vue";
import { defineStore } from "pinia";

export const useExporterTestStore = defineStore("exporterTest", () => {
  const results = ref({});

  // Results control
  function addResult(url, statusCode) {
    results.value[url] = statusCode;
  }

  function setResults(newResults) {
    results.value = { ...newResults };
  }

  return { results, addResult, setResults };
});
