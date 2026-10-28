<script setup lang="ts">
import { ref } from "vue";
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
import Terminal from "./components/Terminal.vue";
import Atmosphere from "./components/Atmosphere.vue";
import ServerCore from "./components/ServerCore.vue";
import { useSpotlight } from "./composables/useSpotlight";
useSpotlight();
const menu = ref(false);
const reduced = useReducedMotion();
const repo = "https://github.com/rxzsu/vps-linux";
const release = `${repo}/releases/tag/v0.1`;
const asset = `${repo}/releases/download/v0.1/vps-linux-v0.1-release.qcow2`;
const features = [
  {
    icon: Box,
    title: "Containers, out of the box.",
    text: "Docker Engine and Compose V2. A clean foundation for the services you want to run.",
    label: "01 / CONTAINERS",
    wide: true,
  },
  {
    icon: Cloud,
    title: "First boot. Your rules.",
    text: "Use cloud-init to provision your instance and supply your SSH public key.",
    label: "02 / PROVISIONING",
  },
  {
    icon: KeyRound,
    title: "Keys are the default.",
    text: "Public-key SSH authentication. Password authentication and direct root SSH login disabled.",
    label: "03 / ACCESS",
  },
  {
    icon: MemoryStick,
    title: "Make room for more.",
    text: "1 GiB ZRAM with LZ4 compression, alongside a focused Debian 13 base.",
    label: "04 / MEMORY",
  },
  {
    icon: Cpu,
    title: "At home in a VM.",
    text: "QCOW2 for QEMU/KVM. UEFI boot with GRUB and an 8 GiB virtual disk.",
    label: "05 / VIRTUALIZATION",
    wide: true,
  },
];
const layers = [
  { icon: Cpu, title: "QEMU / KVM", sub: "Virtual hardware" },
  { icon: Layers, title: "UEFI / GRUB", sub: "Boot foundation" },
  { icon: TerminalSquare, title: "Debian 13", sub: "Linux 6.12" },
  {
    icon: Cloud,
    title: "systemd + cloud-init",
    sub: "Services & provisioning",
  },
  { icon: Box, title: "Docker workloads", sub: "Your next deployment" },
];
const docs = [
  {
    title: "Overview & requirements",
    text: "VPS Linux v0.1 is an independent Debian 13 (Trixie), x86_64 image. Use QEMU/KVM-compatible virtualization with UEFI support. The tested configuration is 2 vCPUs and 2 GiB RAM; the image has an 8 GiB virtual disk.",
  },
  {
    title: "Download & verify",
    text: "Download the QCOW2 image and its SHA256 file from the same v0.1 GitHub release. In the download directory, verify the image before importing it:",
    code: "sha256sum -c vps-linux-v0.1-release.qcow2.sha256",
  },
  {
    title: "Boot with QEMU/KVM",
    text: "Import the QCOW2 disk into a QEMU/KVM virtual machine. Configure UEFI firmware, 2 virtual CPUs and 2 GiB memory. Attach your cloud-init NoCloud data source before first boot. Exact QEMU flags and firmware paths depend on the host; the project has not published a verified launch command.",
  },
  {
    title: "cloud-init & SSH provisioning",
    text: "Provide your public SSH key through cloud-init at first boot. Keep the private key on your own machine. Password SSH authentication and direct root SSH login are disabled. A verified user-data template and default login username are not yet documented; confirm these before deployment.",
  },
  {
    title: "Docker & Compose",
    text: "The image includes Docker Engine and Docker Compose V2. After logging into the instance, inspect the installed versions and daemon status. Docker permissions depend on the provisioned user.",
    code: "docker --version\ndocker compose version\nsystemctl is-active docker",
  },
  {
    title: "Networking & security",
    text: "systemd-networkd provides DHCP networking; systemd-resolved handles DNS and systemd-timesyncd handles time synchronization. SSH key authentication is a starting point: review updates, firewall rules and workload exposure for your own deployment.",
  },
  {
    title: "Known limitations",
    text: "v0.1 was assembled and tested manually. Reproducible build scripts and an automated image build pipeline are not available. Cloud providers must support custom QCOW2 import or a compatible conversion workflow. Compatibility with every provider is not guaranteed.",
  },
];
const copied = ref("");
async function copy(code: string) {
  try {
    await navigator.clipboard.writeText(code);
    copied.value = code;
    setTimeout(() => (copied.value = ""), 2000);
  } catch {
    copied.value = "Clipboard unavailable. Select the command to copy.";
  }
}
</script>

<template>
  <a class="skip" href="#main">Skip to content</a>
  <header>
    <nav class="nav shell" aria-label="Main navigation">
      <a class="brand" href="#" aria-label="VPS Linux home"
        ><svg viewBox="0 0 40 40" aria-hidden="true">
          <path d="m6 10 14 23 14-23M13 10l7 12 7-12" /></svg
        ><span
          >vps<span class="brand-light">linux</span
          ><span class="brand-dot">.</span></span
        ></a
      >
      <div class="nav-links" :class="{ open: menu }">
        <a href="#features" @click="menu = false">Features</a
        ><a href="#architecture" @click="menu = false">Architecture</a
        ><a href="#documentation" @click="menu = false">Documentation</a
        ><a :href="repo" @click="menu = false"
          >GitHub <ArrowUpRight :size="13"
        /></a>
      </div>
      <a class="nav-download" href="#download"
        >Get VPS Linux <ArrowUpRight :size="15" /></a
      ><button
        class="menu-toggle"
        :aria-expanded="menu"
        aria-label="Toggle navigation"
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
          ><span class="status-dot"></span> VPS Linux v0.1 is here
          <span class="pill-divider"></span> Meet the release
          <ArrowRight :size="13"
        /></a>
        <div class="eyebrow hero-eyebrow">
          A SMALLER FOUNDATION. A BIGGER POSSIBILITY.
        </div>
        <h1>
          Your server.<br /><span class="gradient-text"
            >Nothing<br class="hero-title-break" />
            unnecessary.</span
          >
        </h1>
        <p class="hero-description">
          A lightweight Debian-powered Linux image for virtual servers, Docker
          workloads, and clean infrastructure.<br class="desktop-break" />
          Minimal by design. Ready to build on.
        </p>
        <div class="hero-actions">
          <a class="button primary" :href="asset"
            ><Download :size="17" /> Download v0.1
            <ArrowUpRight :size="16" /></a
          ><a class="button secondary" :href="repo"
            ><Github :size="17" /> Explore on GitHub</a
          >
        </div>
        <div class="hero-meta">
          <span><Check /> Debian 13</span><span><Check /> Docker ready</span
          ><span><Check /> Cloud-init</span><span><Check /> QEMU/KVM</span>
        </div></motion.div
      >
      <motion.div
        class="hero-visual"
        :initial="reduced ? false : { opacity: 0, y: 30 }"
        :animate="{ opacity: 1, y: 0 }"
        :transition="{ duration: 0.8, delay: 0.2 }"
        ><div class="visual-label">
          <span class="status-dot"></span> LESS OVERHEAD. MORE CONTROL.
        </div>
        <ServerCore /><Terminal />
        <div class="visual-caption">
          <span>Purpose-built for the work that matters.</span
          ><span>01 — FOUNDATION</span>
        </div></motion.div
      >
      <div class="hero-bottom">
        <span>THE ESSENTIALS. ALREADY IN PLACE.</span>
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
          <div class="eyebrow">01 / THE FOUNDATION</div>
          <h2>
            Everything you need.<br /><span>Space for what you build.</span>
          </h2>
        </div>
        <p>
          No desktop. No unnecessary layers.<br />Just a focused set of tools
          for a server<br />that feels like your own.
        </p>
      </div>
      <div class="feature-grid">
        <motion.article
          v-for="feature in features"
          :key="feature.title"
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
            <span>app</span><span>api</span><span>database</span
            ><span>your idea</span>
          </div>
          <div v-if="feature.label.startsWith('05')" class="vm-spec">
            <span>x86_64</span><span>UEFI</span><span>QCOW2</span
            ><span>8 GiB disk</span>
          </div></motion.article
        >
      </div>
    </section>
    <section id="architecture" class="architecture section">
      <div class="shell">
        <div class="section-intro">
          <div>
            <div class="eyebrow">02 / UNDER THE HOOD</div>
            <h2>A clear path.<br /><span>From boot to workload.</span></h2>
          </div>
          <p>
            Familiar components. Deliberate choices.<br />A stack you can
            understand<br />and make your own.
          </p>
        </div>
        <div class="architecture-flow">
          <div class="architecture-beam" aria-hidden="true"></div>
          <motion.div
            v-for="(layer, i) in layers"
            :key="layer.title"
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
          <span>/</span> Linux 6.12 <span>/</span> No hidden complexity
        </div>
      </div>
    </section>
    <section class="philosophy shell section">
      <div class="eyebrow">03 / THE PHILOSOPHY</div>
      <div class="philosophy-content">
        <h2>Built to run services.<br /><span>Not distractions.</span></h2>
        <div>
          <p>
            Infrastructure should give you a starting point, then get out of
            your way.
          </p>
          <p>
            VPS Linux keeps the base minimal, the configuration predictable, and
            the decisions in your hands. For your homelab, your next container
            stack, or a clean place to experiment.
          </p>
          <a :href="repo"
            >Open source. Open possibilities. <ArrowUpRight :size="17"
          /></a>
        </div>
      </div>
      <div class="principles">
        <span><span>01</span> Minimal by design</span
        ><span><span>02</span> Predictable by default</span
        ><span><span>03</span> Yours to control</span>
      </div>
    </section>
    <section id="download" class="shell section">
      <div class="download-panel">
        <div>
          <div class="eyebrow">
            <span class="status-dot"></span> AVAILABLE NOW / v0.1
          </div>
          <h2>Your next deployment<br />starts with a clean slate.</h2>
          <p>Get the image. Bring your ideas.</p>
          <div class="download-specs">
            <span>Debian 13</span><span>x86_64</span><span>QCOW2</span
            ><span>8 GiB virtual disk</span>
          </div>
          <div class="hero-actions">
            <a class="button primary" :href="asset"
              ><Download :size="18" /> Download v0.1
              <ArrowUpRight :size="16" /></a
            ><a class="checksum" :href="`${asset}.sha256`"
              >SHA256 checksum <ArrowUpRight :size="14"
            /></a>
          </div>
          <p class="download-note">
            For QEMU/KVM. Cloud providers require custom QCOW2 import<br />or a
            compatible conversion workflow.
          </p>
        </div>
        <div class="release-manifest">
          <div>
            <span>RELEASE MANIFEST</span><span class="version-tag">v0.1</span>
          </div>
          <dl>
            <div>
              <dt>Distribution</dt>
              <dd>Debian 13 / Trixie</dd>
            </div>
            <div>
              <dt>Kernel</dt>
              <dd>Linux 6.12</dd>
            </div>
            <div>
              <dt>Architecture</dt>
              <dd>x86_64</dd>
            </div>
            <div>
              <dt>Boot</dt>
              <dd>UEFI + GRUB</dd>
            </div>
            <div>
              <dt>Tested VM</dt>
              <dd>2 vCPU / 2 GiB RAM</dd>
            </div>
            <div>
              <dt>Build process</dt>
              <dd>Manually assembled</dd>
            </div>
          </dl>
          <a :href="release"
            >Read the release notes <ArrowUpRight :size="16"
          /></a>
        </div>
      </div>
    </section>
    <section id="documentation" class="shell section documentation">
      <div class="section-intro">
        <div>
          <div class="eyebrow">04 / GET STARTED</div>
          <h2>A little context.<br /><span>A confident first boot.</span></h2>
        </div>
        <p>
          The essentials for working with v0.1.<br />Start here, then make it
          yours.
        </p>
      </div>
      <div class="docs-list">
        <details v-for="(doc, i) in docs" :key="doc.title" :open="i === 0">
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
                  copied === doc.code ? 'Command copied' : 'Copy command'
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
            ? copied.startsWith("Clipboard")
              ? copied
              : "Command copied"
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
      <p>Less overhead. More control.</p>
      <div>
        <a :href="repo">GitHub <ArrowUpRight :size="13" /></a
        ><a :href="release">Releases</a
        ><a href="#documentation">Documentation</a
        ><a :href="`${repo}/blob/main/LICENSE`">MIT License</a>
      </div>
    </div>
    <div class="footer-bottom">
      <span>An independent, open-source Linux project.</span
      ><span><span class="status-dot"></span> VPS Linux v0.1</span
      ><a href="#">Back to top ↑</a>
    </div>
  </footer>
</template>
