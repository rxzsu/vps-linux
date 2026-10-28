import { createApp } from "vue";
import App from "./App.vue";
import { initializeLocaleMetadata } from "./composables/useLocale";
import "./style.css";
import "./effects.css";
initializeLocaleMetadata();
createApp(App).mount("#app");
