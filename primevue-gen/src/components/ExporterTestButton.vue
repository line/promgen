<script setup>
/**
 * Exporter Test button for Forms.
 *
 * Acts like a regular form submit button, but hijacks the button click and submits it to an
 * alternate URL for testing.
 */
import { useExporterTestStore } from "../stores/exporterTest.js";

const props = defineProps({
  href: {
    type: String,
    default: "",
  },
});

const onTestSubmit = (event) => {
  // Find the parent form our button belongs to so that we can simulate a form submission
  const form = new FormData(event.srcElement.closest("form"));
  fetch(props.href, { body: form, method: "post" })
    .then((result) => result.json())
    .then((result) => {
      const exporterTestStore = useExporterTestStore();
      exporterTestStore.setResults(result);
    })
    .catch((error) => alert(error));
};
</script>

<template>
  <button @click.prevent="onTestSubmit"><slot /></button>
</template>
