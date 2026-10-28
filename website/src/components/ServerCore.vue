<template>
  <div class="server-scene" aria-hidden="true">
    <div class="orbit orbit-outer"></div>
    <div class="orbit orbit-inner"></div>
    <svg class="circuit-traces" viewBox="0 0 560 380" fill="none">
      <defs>
        <linearGradient
          id="trace"
          x1="0"
          y1="0"
          x2="560"
          y2="380"
          gradientUnits="userSpaceOnUse"
        >
          <stop stop-color="#7ae9db" stop-opacity="0" />
          <stop offset=".5" stop-color="#7ae9db" />
          <stop offset="1" stop-color="#9180ff" stop-opacity="0" />
        </linearGradient>
      </defs>
      <path
        class="trace-base"
        d="M0 115H110L180 185H280M560 95H430L340 185H280M30 320H155L235 240M550 305H420L330 240"
      />
      <path
        class="trace-flow"
        d="M0 115H110L180 185H280M560 95H430L340 185H280M30 320H155L235 240M550 305H420L330 240"
      />
      <circle cx="110" cy="115" r="3" fill="#79d5cf" />
      <circle cx="430" cy="95" r="3" fill="#a293ef" />
      <circle cx="155" cy="320" r="3" fill="#79d5cf" />
      <circle cx="420" cy="305" r="3" fill="#79d5cf" />
    </svg>
    <div class="core-halo"></div>
    <div class="server-stack">
      <div class="server-slab slab-bottom">
        <div class="slab-face">
          <span>VIRTUAL HARDWARE</span><i></i><i></i><i></i>
        </div>
      </div>
      <div class="server-slab slab-middle">
        <div class="slab-face">
          <span>DEBIAN 13 / LINUX 6.12</span><i></i><i></i><i></i>
        </div>
      </div>
      <div class="server-slab slab-top">
        <div class="core-symbol">
          <svg viewBox="0 0 80 80">
            <path d="m10 18 30 49 30-49M26 18l14 24 14-24" /></svg
          ><span>VPS LINUX</span>
        </div>
        <div class="slab-face">
          <span>YOUR NEXT DEPLOYMENT</span><i></i><i></i><i></i>
        </div>
      </div>
    </div>
    <div class="scene-tag scene-tag-left">
      <span class="status-dot"></span> MINIMAL BASE
    </div>
    <div class="scene-tag scene-tag-right">
      <span class="status-dot"></span> MAXIMUM POSSIBILITY
    </div>
    <div class="scene-coordinate">SYS.01 <span> // </span> x86_64</div>
  </div>
</template>
