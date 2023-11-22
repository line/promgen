import { ref } from "vue";
import { defineStore } from "pinia";

export const useSilenceStore = defineStore("silence", () => {
  const formVisible = ref(false);
  const labels = ref({});

  // Silence form visibility control
  function showForm() {
    formVisible.value = true;
  }

  function hideForm() {
    formVisible.value = false;
  }

  // Labels control
  function addLabel(label, value) {
    labels.value[label] = value;
  }

  function removeLabel(label) {
    delete labels.value[label];
  }

  function setLabels(newLabels) {
    labels.value = { ...newLabels };
  }

  return { formVisible, labels, showForm, hideForm, addLabel, removeLabel, setLabels };
});
