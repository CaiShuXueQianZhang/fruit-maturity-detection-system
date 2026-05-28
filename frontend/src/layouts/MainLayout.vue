<template>
  <div class="main-layout">
    <aside class="sidebar">
      <slot name="sidebar"></slot>
    </aside>

    <div class="main-container">
      <header class="header">
        <slot name="header"></slot>
      </header>

      <main class="content">
        <slot name="content"></slot>
      </main>
    </div>
  </div>
</template>

<script setup></script>

<style scoped>
.main-layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
  background: transparent;
}

.sidebar {
  width: 240px;
  background: linear-gradient(180deg, rgba(8,16,22,0.6), rgba(6,12,18,0.5));
  border-right: 1px solid rgba(255,255,255,0.03);
  display: flex;
  flex-direction: column;
  padding-top: 10px;
}

.main-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.header {
  height: 72px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  background: linear-gradient(90deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01));
  backdrop-filter: blur(6px);
  border-bottom: 1px solid rgba(255,255,255,0.02);
}

.content {
  flex: 1;
  padding: 24px 32px;
  overflow-y: auto;
  background: transparent;
}
</style>
