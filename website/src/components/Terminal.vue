<script setup lang="ts">
import { useLocale } from "../composables/useLocale";
const { t } = useLocale();
import { ref, onMounted, onUnmounted } from "vue";
const lines = [
  ["$ cat /etc/os-release", 'PRETTY_NAME="Debian GNU/Linux 13 (trixie)"'],
  ["$ systemctl is-active docker", "active"],
  ["$ uname -m", "x86_64"],
];
const count = ref(1);
const typed = ref(0);
let timer: ReturnType<typeof setInterval> | undefined;
onMounted(() => {
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    count.value = lines.length;
    typed.value = 100;
  } else
    timer = setInterval(() => {
      const current = lines[count.value - 1]!;
      if (typed.value < current[0]!.length + 18) typed.value++;
      else if (count.value < lines.length) {
        count.value++;
        typed.value = 0;
      } else clearInterval(timer);
    }, 45);
});
onUnmounted(() => clearInterval(timer));
</script>
<template>
  <div class="terminal">
    <div class="terminal-bar">
      <div class="dots"><i></i><i></i><i></i></div>
      <span>vps@linux: ~</span><span class="demo">{{ t("DEMO") }}</span>
    </div>
    <div class="terminal-body" :aria-label="t('Simulated terminal output')">
      <div
        v-for="(line, i) in lines.slice(0, count)"
        :key="i"
        class="terminal-line"
      >
        <div class="command">
          {{ i === count - 1 ? line[0]?.slice(0, typed) : line[0] }}
        </div>
        <div
          v-if="i < count - 1 || typed >= (line[0]?.length ?? 0)"
          class="output"
        >
          {{ line[1] }}
        </div>
      </div>
      <span class="prompt">$ <span class="cursor">▍</span></span>
    </div>
    <div class="terminal-bottom">
      <span><b>●</b>{{ t("All systems ready") }}</span
      ><span>x86_64 / UEFI</span>
    </div>
  </div>
</template>
