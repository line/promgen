import Vue from "vue";

import { createI18n } from "vue-i18n";
import { en } from "./locales/en.js";
import { ja } from "./locales/ja.js";
import { matchBrowserLocale } from "./utils/matchBrowserLocale.js";

import { createPinia } from "pinia";
import { useExporterTestStore } from "./stores/exporterTest.js";
import { useSilenceStore } from "./stores/silence.js";

import PrimeVue from "primevue/config";
import "primevue/resources/themes/bootstrap4-light-blue/theme.css";

import BootstrapPanel from "./components/BootstrapPanel.vue";
import ExporterTestButton from "./components/ExporterTestButton.vue";
import ExporterTestResult from "./components/ExporterTestResult.vue";
import SilenceForm from "./components/SilenceForm.vue";

const i18n = createI18n({
  locale: matchBrowserLocale(["en", "ja"]),
  fallbackLocale: "en",
  messages: {
    en,
    ja,
  },
});

window.useExporterTestStore = useExporterTestStore;
window.useSilenceStore = useSilenceStore;

window.createPrimeVueApp = function (opt) {
  const app = Vue.createApp(opt);

  app.use(i18n);
  app.use(createPinia());
  app.use(PrimeVue);

  app.component("BootstrapPanel", BootstrapPanel);
  app.component("ExporterTestButton", ExporterTestButton);
  app.component("ExporterTestResult", ExporterTestResult);
  app.component("SilenceForm", SilenceForm);

  return app;
};
