<script setup lang="ts">
import { ref, computed } from "vue";
import { motion, useReducedMotion } from "motion-v";
import {
  ArrowUpRight,
  ArrowRight,
  Download,
  CodeXml as Github,
  Menu,
  X,
  Layers,
  Box,
  Cloud,
  KeyRound,
  MemoryStick,
  Cpu,
  Check,
  Copy,
  ChevronRight,
  TerminalSquare,
} from "@lucide/vue";
import { useLocale } from "./composables/useLocale";
import Terminal from "./components/Terminal.vue";
import Atmosphere from "./components/Atmosphere.vue";
import ServerCore from "./components/ServerCore.vue";
import { useSpotlight } from "./composables/useSpotlight";
useSpotlight();
const { locale, t, setLocale } = useLocale();
const menu = ref(false);
const reduced = useReducedMotion();
const repo = "https://github.com/rxzsu/vps-linux";
const release = `${repo}/releases/tag/v0.1`;
const asset = `${repo}/releases/download/v0.1/vps-linux-v0.1-release.qcow2`;
const features = computed(() => [
  {
    icon: Box,
    title: t("Containers, out of the box."),
    text: t(
      "Docker Engine and Compose V2. A clean foundation for the services you want to run.",
    ),
    label: t("01 / CONTAINERS"),
    wide: true,
  },
  {
    icon: Cloud,
    title: t("First boot. Your rules."),
    text: t(
      "Use cloud-init to provision your instance and supply your SSH public key.",
    ),
    label: t("02 / PROVISIONING"),
  },
  {
    icon: KeyRound,
    title: t("Keys are the default."),
    text: t(
      "Public-key SSH authentication. Password authentication and direct root SSH login disabled.",
    ),
    label: t("03 / ACCESS"),
  },
  {
    icon: MemoryStick,
    title: t("Make room for more."),
    text: t(
      "1 GiB ZRAM with LZ4 compression, alongside a focused Debian 13 base.",
    ),
    label: t("04 / MEMORY"),
  },
  {
    icon: Cpu,
    title: t("At home in a VM."),
    text: t(
      "QCOW2 for QEMU/KVM. UEFI boot with GRUB and an 8 GiB virtual disk.",
    ),
    label: t("05 / VIRTUALIZATION"),
    wide: true,
  },
]);
const layers = computed(() => [
  { icon: Cpu, title: "QEMU / KVM", sub: t("Virtual hardware") },
  { icon: Layers, title: "UEFI / GRUB", sub: t("Boot foundation") },
  { icon: TerminalSquare, title: "Debian 13", sub: "Linux 6.12" },
  {
    icon: Cloud,
    title: "systemd + cloud-init",
    sub: t("Services & provisioning"),
  },
  { icon: Box, title: t("Docker workloads"), sub: t("Your next deployment") },
]);
const docs = computed(() => [
  {
    title: t("Overview & requirements"),
    text: t(
      "VPS Linux v0.1 is an independent Debian 13 (Trixie), x86_64 image. Use QEMU/KVM-compatible virtualization with UEFI support. The tested configuration is 2 vCPUs and 2 GiB RAM; the image has an 8 GiB virtual disk.",
    ),
  },
  {
    title: t("Download & verify"),
    text: t(
      "Download the QCOW2 image and its SHA256 file from the same v0.1 GitHub release. In the download directory, verify the image before importing it:",
    ),
    code: "sha256sum -c vps-linux-v0.1-release.qcow2.sha256",
  },
  {
    title: t("Boot with QEMU/KVM"),
    text: t(
      "Import the QCOW2 disk into a QEMU/KVM virtual machine. Configure UEFI firmware, 2 virtual CPUs and 2 GiB memory. Attach your cloud-init NoCloud data source before first boot. Exact QEMU flags and firmware paths depend on the host; the project has not published a verified launch command.",
    ),
  },
  {
    title: t("cloud-init & SSH provisioning"),
    text: t(
      "Provide your public SSH key through cloud-init at first boot. Keep the private key on your own machine. Password SSH authentication and direct root SSH login are disabled. A verified user-data template and default login username are not yet documented; confirm these before deployment.",
    ),
  },
  {
    title: t("Docker & Compose"),
    text: t(
      "The image includes Docker Engine and Docker Compose V2. After logging into the instance, inspect the installed versions and daemon status. Docker permissions depend on the provisioned user.",
    ),
    code: "docker --version\ndocker compose version\nsystemctl is-active docker",
  },
  {
    title: t("Networking & security"),
    text: t(
      "systemd-networkd provides DHCP networking; systemd-resolved handles DNS and systemd-timesyncd handles time synchronization. SSH key authentication is a starting point: review updates, firewall rules and workload exposure for your own deployment.",
    ),
  },
  {
    title: t("Known limitations"),
    text: t(
      "v0.1 was assembled and tested manually. Reproducible build scripts and an automated image build pipeline are not available. Cloud providers must support custom QCOW2 import or a compatible conversion workflow. Compatibility with every provider is not guaranteed.",
    ),
  },
]);
const copied = ref("");
async function copy(code: string) {
  try {
    await navigator.clipboard.writeText(code);
    copied.value = code;
    setTimeout(() => (copied.value = ""), 2000);
  } catch {
    copied.value = "error";
  }
}
</script>

<template>
  <a class="skip" href="#main">{{ t("Skip to content") }}</a>
  <header>
    <nav class="nav shell" :aria-label="t('Main navigation')">
      <a class="brand" href="#" :aria-label="t('VPS Linux home')"
        ><svg viewBox="0 0 40 40" aria-hidden="true">
          <path d="m6 10 14 23 14-23M13 10l7 12 7-12" /></svg
        ><span
          >vps<span class="brand-light">linux</span
          ><span class="brand-dot">.</span></span
        ></a
      >
      <div class="nav-links" :class="{ open: menu }">
        <a href="#features" @click="menu = false">{{ t("Features") }}</a
        ><a href="#architecture" @click="menu = false">{{
          t("Architecture")
        }}</a
        ><a href="#documentation" @click="menu = false">{{
          t("Documentation")
        }}</a
        ><a :href="repo" @click="menu = false"
          >GitHub <ArrowUpRight :size="13"
        /></a>
      </div>
      <div
        class="language-switch"
        role="group"
        :aria-label="t('Site language')"
      >
        <button
          type="button"
          lang="ru"
          aria-label="Русский"
          :aria-pressed="locale === 'ru'"
          @click="setLocale('ru')"
        >
          RU
        </button>
        <button
          type="button"
          lang="en"
          aria-label="English"
          :aria-pressed="locale === 'en'"
          @click="setLocale('en')"
        >
          EN
        </button>
      </div>
      <a class="nav-download" href="#download"
        >{{ t("Get VPS Linux") }}<ArrowUpRight :size="15" /></a
      ><button
        class="menu-toggle"
        :aria-expanded="menu"
        :aria-label="t('Toggle navigation')"
        @click="menu = !menu"
      >
        <X v-if="menu" /><Menu v-else />
      </button>
    </nav>
  </header>
  <main id="main">
    <section class="hero shell">
      <Atmosphere />
      <motion.div
        :initial="reduced ? false : { opacity: 0, y: 20 }"
        :animate="{ opacity: 1, y: 0 }"
        :transition="{ duration: 0.65 }"
        class="hero-copy"
        ><a class="release-pill" :href="release"
          ><span class="status-dot"></span>{{ t("VPS Linux v0.1 is here")
          }}<span class="pill-divider"></span>{{ t("Meet the release")
          }}<ArrowRight :size="13"
        /></a>
        <div class="eyebrow hero-eyebrow">
          {{ t("A SMALLER FOUNDATION. A BIGGER POSSIBILITY.") }}
        </div>
        <h1>
          {{ t("Your server.") }}<br /><span class="gradient-text"
            >{{ t("Nothing") }}<br class="hero-title-break" />
            {{ t("unnecessary.") }}</span
          >
        </h1>
        <p class="hero-description">
          {{
            t(
              "A lightweight Debian-powered Linux image for virtual servers, Docker workloads, and clean infrastructure. Minimal by design. Ready to build on.",
            )
          }}
        </p>
        <div class="hero-actions">
          <a class="button primary" :href="asset"
            ><Download :size="17" />{{ t("Download v0.1")
            }}<ArrowUpRight :size="16" /></a
          ><a class="button secondary" :href="repo"
            ><Github :size="17" />{{ t("Explore on GitHub") }}</a
          >
        </div>
        <div class="hero-meta">
          <span><Check /> Debian 13</span
          ><span><Check />{{ t("Docker ready") }}</span
          ><span><Check /> Cloud-init</span><span><Check /> QEMU/KVM</span>
        </div></motion.div
      >
      <motion.div
        class="hero-visual"
        :initial="reduced ? false : { opacity: 0, y: 30 }"
        :animate="{ opacity: 1, y: 0 }"
        :transition="{ duration: 0.8, delay: 0.2 }"
        ><div class="visual-label">
          <span class="status-dot"></span
          >{{ t("LESS OVERHEAD. MORE CONTROL.") }}
        </div>
        <ServerCore /><Terminal />
        <div class="visual-caption">
          <span>{{ t("Purpose-built for the work that matters.") }}</span
          ><span>{{ t("01 — FOUNDATION") }}</span>
        </div></motion.div
      >
      <div class="hero-bottom">
        <span>{{ t("THE ESSENTIALS. ALREADY IN PLACE.") }}</span>
        <div>
          <span>debian <b>13</b></span
          ><span><Box :size="19" /> Docker</span
          ><span><Cloud :size="21" /> cloud-init</span
          ><span>QEMU<span class="muted"> / KVM</span></span>
        </div>
      </div>
    </section>
    <section id="features" class="section shell">
      <div class="section-intro">
        <div>
          <div class="eyebrow">{{ t("01 / THE FOUNDATION") }}</div>
          <h2>
            {{ t("Everything you need.") }}<br /><span>{{
              t("Space for what you build.")
            }}</span>
          </h2>
        </div>
        <p>
          {{
            t(
              "No desktop. No unnecessary layers. Just a focused set of tools for a server that feels like your own.",
            )
          }}
        </p>
      </div>
      <div class="feature-grid">
        <motion.article
          v-for="(feature, i) in features"
          :key="i"
          :class="['feature', { wide: feature.wide }]"
          :initial="reduced ? false : { opacity: 0, y: 18 }"
          :while-in-view="{ opacity: 1, y: 0 }"
          :in-view-options="{ once: true }"
          :transition="{ duration: 0.45 }"
          ><div class="feature-top">
            <component
              :is="feature.icon"
              :size="27"
              :stroke-width="1.4"
            /><span>{{ feature.label }}</span>
          </div>
          <h3>{{ feature.title }}</h3>
          <p>{{ feature.text }}</p>
          <div
            v-if="feature.label.startsWith('01')"
            class="container-blocks"
            aria-hidden="true"
          >
            <span>{{ t("app") }}</span
            ><span>{{ t("api") }}</span
            ><span>{{ t("database") }}</span
            ><span>{{ t("your idea") }}</span>
          </div>
          <div v-if="feature.label.startsWith('05')" class="vm-spec">
            <span>x86_64</span><span>UEFI</span><span>QCOW2</span
            ><span>{{ t("8 GiB disk") }}</span>
          </div></motion.article
        >
      </div>
    </section>
    <section id="architecture" class="architecture section">
      <div class="shell">
        <div class="section-intro">
          <div>
            <div class="eyebrow">{{ t("02 / UNDER THE HOOD") }}</div>
            <h2>
              {{ t("A clear path.") }}<br /><span>{{
                t("From boot to workload.")
              }}</span>
            </h2>
          </div>
          <p>
            {{
              t(
                "Familiar components. Deliberate choices. A stack you can understand and make your own.",
              )
            }}
          </p>
        </div>
        <div class="architecture-flow">
          <div class="architecture-beam" aria-hidden="true"></div>
          <motion.div
            v-for="(layer, i) in layers"
            :key="i"
            class="layer"
            :initial="reduced ? false : { opacity: 0, y: 15 }"
            :while-in-view="{ opacity: 1, y: 0 }"
            :in-view-options="{ once: true }"
            :transition="{ delay: reduced ? 0 : i * 0.08 }"
            ><span class="layer-number">0{{ i + 1 }}</span
            ><component :is="layer.icon" :size="29" :stroke-width="1.3" />
            <h3>{{ layer.title }}</h3>
            <p>{{ layer.sub }}</p>
            <ArrowRight v-if="i < 4" class="layer-arrow" :size="17"
          /></motion.div>
        </div>
        <div class="architecture-note">
          <span class="status-dot"></span> Debian 13 (Trixie)
          <span>/</span> Linux 6.12 <span>/</span
          >{{ t("No hidden complexity") }}
        </div>
      </div>
    </section>
    <section class="philosophy shell section">
      <div class="eyebrow">{{ t("03 / THE PHILOSOPHY") }}</div>
      <div class="philosophy-content">
        <h2>
          {{ t("Built to run services.") }}<br /><span>{{
            t("Not distractions.")
          }}</span>
        </h2>
        <div>
          <p>
            {{
              t(
                "Infrastructure should give you a starting point, then get out of your way.",
              )
            }}
          </p>
          <p>
            {{
              t(
                "VPS Linux keeps the base minimal, the configuration predictable, and the decisions in your hands. For your homelab, your next container stack, or a clean place to experiment.",
              )
            }}
          </p>
          <a :href="repo"
            >{{ t("Open source. Open possibilities.")
            }}<ArrowUpRight :size="17"
          /></a>
        </div>
      </div>
      <div class="principles">
        <span><span>01</span>{{ t("Minimal by design") }}</span
        ><span><span>02</span>{{ t("Predictable by default") }}</span
        ><span><span>03</span>{{ t("Yours to control") }}</span>
      </div>
    </section>
    <section id="download" class="shell section">
      <div class="download-panel">
        <div>
          <div class="eyebrow">
            <span class="status-dot"></span>{{ t("AVAILABLE NOW / v0.1") }}
          </div>
          <h2>
            {{ t("Your next deployment") }}<br />{{
              t("starts with a clean slate.")
            }}
          </h2>
          <p>{{ t("Get the image. Bring your ideas.") }}</p>
          <div class="download-specs">
            <span>Debian 13</span><span>x86_64</span><span>QCOW2</span
            ><span>{{ t("8 GiB virtual disk") }}</span>
          </div>
          <div class="hero-actions">
            <a class="button primary" :href="asset"
              ><Download :size="18" />{{ t("Download v0.1")
              }}<ArrowUpRight :size="16" /></a
            ><a class="checksum" :href="`${asset}.sha256`"
              >{{ t("SHA256 checksum") }}<ArrowUpRight :size="14"
            /></a>
          </div>
          <p class="download-note">
            {{ t("For QEMU/KVM. Cloud providers require custom QCOW2 import")
            }}<br />{{ t("or a compatible conversion workflow.") }}
          </p>
        </div>
        <div class="release-manifest">
          <div>
            <span>{{ t("RELEASE MANIFEST") }}</span
            ><span class="version-tag">v0.1</span>
          </div>
          <dl>
            <div>
              <dt>{{ t("Distribution") }}</dt>
              <dd>Debian 13 / Trixie</dd>
            </div>
            <div>
              <dt>{{ t("Kernel") }}</dt>
              <dd>Linux 6.12</dd>
            </div>
            <div>
              <dt>{{ t("Architecture") }}</dt>
              <dd>x86_64</dd>
            </div>
            <div>
              <dt>{{ t("Boot") }}</dt>
              <dd>UEFI + GRUB</dd>
            </div>
            <div>
              <dt>{{ t("Tested VM") }}</dt>
              <dd>{{ t("2 vCPU / 2 GiB RAM") }}</dd>
            </div>
            <div>
              <dt>{{ t("Build process") }}</dt>
              <dd>{{ t("Manually assembled") }}</dd>
            </div>
          </dl>
          <a :href="release"
            >{{ t("Read the release notes") }}<ArrowUpRight :size="16"
          /></a>
        </div>
      </div>
    </section>
    <section id="documentation" class="shell section documentation">
      <div class="section-intro">
        <div>
          <div class="eyebrow">{{ t("04 / GET STARTED") }}</div>
          <h2>
            {{ t("A little context.") }}<br /><span>{{
              t("A confident first boot.")
            }}</span>
          </h2>
        </div>
        <p>
          {{
            t(
              "The essentials for working with v0.1. Start here, then make it yours.",
            )
          }}
        </p>
      </div>
      <div class="docs-list">
        <details v-for="(doc, i) in docs" :key="i" :open="i === 0">
          <summary>
            <span class="doc-number">0{{ i + 1 }}</span
            >{{ doc.title }}<ChevronRight :size="19" />
          </summary>
          <div class="doc-body">
            <p>{{ doc.text }}</p>
            <div v-if="doc.code" class="code-block">
              <pre><code>{{ doc.code }}</code></pre>
              <button
                @click="copy(doc.code)"
                :aria-label="
                  copied === doc.code ? t('Command copied') : t('Copy command')
                "
              >
                <Check v-if="copied === doc.code" :size="16" /><Copy
                  v-else
                  :size="16"
                />
              </button>
            </div>
          </div>
        </details>
      </div>
      <p class="sr-only" role="status">
        {{
          copied
            ? copied === "error"
              ? t("Clipboard unavailable. Select the command to copy.")
              : t("Command copied")
            : ""
        }}
      </p>
    </section>
  </main>
  <footer class="shell">
    <div class="footer-top">
      <a class="brand" href="#"
        ><svg viewBox="0 0 40 40" aria-hidden="true">
          <path d="m6 10 14 23 14-23M13 10l7 12 7-12" /></svg
        ><span
          >vps<span class="brand-light">linux</span
          ><span class="brand-dot">.</span></span
        ></a
      >
      <p>{{ t("Less overhead. More control.") }}</p>
      <div>
        <a :href="repo">GitHub <ArrowUpRight :size="13" /></a
        ><a :href="release">{{ t("Releases") }}</a
        ><a href="#documentation">{{ t("Documentation") }}</a
        ><a :href="`${repo}/blob/main/LICENSE`">{{ t("MIT License") }}</a>
      </div>
    </div>
    <div class="footer-bottom">
      <span>{{ t("An independent, open-source Linux project.") }}</span
      ><span><span class="status-dot"></span> VPS Linux v0.1</span
      ><a href="#">{{ t("Back to top ↑") }}</a>
    </div>
  </footer>
</template>
