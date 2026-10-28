<script setup lang="ts">
// Lightweight, original CSS atmosphere inspired by the Aurora / Particles
// visual language of Vue Bits. No WebGL, network assets or animation loop.
const motes = Array.from({ length: 22 }, (_, i) => ({
  left: `${(i * 47 + 11) % 100}%`,
  top: `${(i * 31 + 9) % 100}%`,
  delay: `${-(i * 0.73)}s`,
  duration: `${8 + (i % 5) * 2}s`,
}));
</script>
<template>
  <div class="atmosphere" aria-hidden="true">
    <div class="aurora aurora-cyan"></div>
    <div class="aurora aurora-violet"></div>
    <div class="aurora aurora-blue"></div>
    <div class="perspective-grid"></div>
    <span
      v-for="(mote, i) in motes"
      :key="i"
      class="mote"
      :style="{
        left: mote.left,
        top: mote.top,
        animationDelay: mote.delay,
        animationDuration: mote.duration,
      }"
    ></span>
    <div class="atmosphere-noise"></div>
  </div>
</template>
