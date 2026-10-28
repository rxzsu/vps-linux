import { readonly, ref, watchEffect } from "vue";
import { russian } from "../locales/ru";

export type Locale = "en" | "ru";
type Message = keyof typeof russian;
const storageKey = "vps-linux-language";
const isLocale = (value: unknown): value is Locale =>
  value === "en" || value === "ru";

function initialLocale(): Locale {
  const requested = new URLSearchParams(window.location.search).get("lang");
  if (isLocale(requested)) return requested;
  try {
    const saved = localStorage.getItem(storageKey);
    if (isLocale(saved)) return saved;
  } catch {
    /* Language switching still works when storage is blocked. */
  }
  return navigator.language.toLowerCase().startsWith("ru") ? "ru" : "en";
}

const locale = ref<Locale>(initialLocale());
function t(message: Message): string {
  return locale.value === "ru" ? russian[message] : message;
}
function setLocale(next: Locale) {
  locale.value = next;
  try {
    localStorage.setItem(storageKey, next);
  } catch {
    /* Optional persistence. */
  }
  const url = new URL(window.location.href);
  url.searchParams.set("lang", next);
  window.history.replaceState(window.history.state, "", url);
}

/** Called once from the entrypoint so metadata stays in sync across components. */
export function initializeLocaleMetadata() {
  watchEffect(() => {
    document.documentElement.lang = locale.value;
    document.title = t("VPS Linux — Your server. Nothing unnecessary.");
    const description = t(
      "A lightweight Debian 13 image for QEMU/KVM, Docker workloads and clean infrastructure. Explore VPS Linux v0.2.",
    );
    document
      .querySelector('meta[name="description"]')
      ?.setAttribute("content", description);
    document
      .querySelector('meta[property="og:title"]')
      ?.setAttribute("content", document.title);
    document
      .querySelector('meta[property="og:description"]')
      ?.setAttribute("content", description);
    let ogLocale = document.querySelector('meta[property="og:locale"]');
    if (!ogLocale) {
      ogLocale = document.createElement("meta");
      ogLocale.setAttribute("property", "og:locale");
      document.head.appendChild(ogLocale);
    }
    ogLocale.setAttribute("content", locale.value === "ru" ? "ru_RU" : "en_US");
  });
}

export function useLocale() {
  return { locale: readonly(locale), t, setLocale };
}
