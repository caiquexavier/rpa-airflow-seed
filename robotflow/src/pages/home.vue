<template>
  <div class="home-page">
    <div class="home-container">
      <div class="welcome-section">
        <h1 class="welcome-title">Welcome to RobotFlow</h1>
        <p class="welcome-subtitle">Design and manage your RPA orchestration workflows</p>
      </div>

      <div class="features-grid">
        <div class="feature-card" @click="navigateToDesigner">
          <div class="feature-icon">✏️</div>
          <h3 class="feature-title">Flow Designer</h3>
          <p class="feature-description">
            Create and visualize workflow processes with intuitive flow diagrams.
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  layout: 'default'
});

const navigateToDesigner = (): void => {
  navigateTo('/designer');
};
</script>

<style scoped>
.home-page {
  min-height: 100%;
  padding: 3rem 2rem;
}

.home-container {
  max-width: 1200px;
  margin: 0 auto;
}

.welcome-section {
  text-align: center;
  margin-bottom: 4rem;
  padding: 2rem 0;
}

.welcome-title {
  font-size: 2.5rem;
  font-weight: 700;
  color: #f9fafb;
  margin-bottom: 0.5rem;
  background: linear-gradient(135deg, #0ea5e9 0%, #22c55e 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.welcome-subtitle {
  font-size: 1.125rem;
  color: #9ca3af;
}

.features-grid {
  display: flex;
  justify-content: center;
  gap: 2rem;
}

.feature-card {
  background: rgba(11, 17, 32, 0.4);
  backdrop-filter: blur(10px);
  border-radius: 1rem;
  padding: 3rem;
  transition: all 0.3s;
  cursor: pointer;
  max-width: 400px;
  text-align: center;
}

.feature-card:hover {
  background: rgba(11, 17, 32, 0.6);
  transform: translateY(-4px);
}

.feature-icon {
  font-size: 3rem;
  margin-bottom: 1.5rem;
}

.feature-title {
  font-size: 1.5rem;
  font-weight: 600;
  color: #f9fafb;
  margin-bottom: 1rem;
}

.feature-description {
  font-size: 1rem;
  color: #d1d5db;
  line-height: 1.6;
}
</style>
