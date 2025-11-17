<template>
  <div class="layout-container">
    <header class="app-header">
      <div class="header-left">
        <div class="glowing-dot"></div>
        <div class="header-title">RobotFlow</div>
      </div>
      <div class="header-right">
        <span class="header-subtitle">RPA Workflow Designer</span>
      </div>
    </header>

    <div class="app-body">
      <aside class="sidebar">
        <nav class="sidebar-nav">
          <NuxtLink to="/home" class="nav-item" active-class="active">
            <span class="nav-icon">🏠</span>
            <span class="nav-label">Home</span>
          </NuxtLink>
          <NuxtLink to="/designer" class="nav-item" active-class="active">
            <span class="nav-icon">✏️</span>
            <span class="nav-label">Designer</span>
          </NuxtLink>
        </nav>
      </aside>

      <main class="main-content">
        <slot />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
// Layout with header and sidebar
</script>

<style scoped>
.layout-container {
  height: 100vh;
  width: 100vw;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.app-header {
  background: rgba(11, 17, 32, 0.8);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid rgba(75, 85, 99, 0.3);
  padding: 1rem 2rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  z-index: 100;
  height: 64px;
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.glowing-dot {
  width: 8px;
  height: 8px;
  background: #0ea5e9;
  border-radius: 50%;
  box-shadow: 0 0 8px #0ea5e9, 0 0 16px #0ea5e9;
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

.header-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: #f9fafb;
}

.header-right {
  display: flex;
  align-items: center;
}

.header-subtitle {
  font-size: 0.875rem;
  color: #9ca3af;
}

.app-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.sidebar {
  width: 240px;
  background: #0b1120;
  border-right: 1px solid rgba(75, 85, 99, 0.3);
  padding: 1.5rem 0;
  flex-shrink: 0;
  overflow-y: auto;
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 0 1rem;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  border-radius: 0.5rem;
  color: #d1d5db;
  text-decoration: none;
  transition: all 0.2s;
  font-size: 0.9375rem;
}

.nav-item:hover {
  background: rgba(75, 85, 99, 0.2);
  color: #f9fafb;
}

.nav-item.active {
  background: rgba(14, 165, 233, 0.15);
  color: #0ea5e9;
  border-left: 3px solid #0ea5e9;
}

.nav-icon {
  font-size: 1.25rem;
  width: 24px;
  text-align: center;
}

.nav-label {
  font-weight: 500;
}

.main-content {
  flex: 1;
  overflow-y: auto;
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
}

/* Scrollbar styling */
.sidebar::-webkit-scrollbar {
  width: 6px;
}

.sidebar::-webkit-scrollbar-track {
  background: rgba(17, 24, 39, 0.5);
  border-radius: 3px;
}

.sidebar::-webkit-scrollbar-thumb {
  background: rgba(75, 85, 99, 0.5);
  border-radius: 3px;
}

.sidebar::-webkit-scrollbar-thumb:hover {
  background: rgba(75, 85, 99, 0.7);
}
</style>

