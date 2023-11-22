import Vue from "vue";

import { createPinia } from "pinia";
import { useSilenceStore } from "./stores/silence.js";

import PrimeVue from "primevue/config";
import "primevue/resources/themes/bootstrap4-light-blue/theme.css";

window.useSilenceStore = useSilenceStore;

window.createPrimeVueApp = function (opt) {
  const app = Vue.createApp(opt);

  app.use(createPinia());
  app.use(PrimeVue);

  return app;
};
