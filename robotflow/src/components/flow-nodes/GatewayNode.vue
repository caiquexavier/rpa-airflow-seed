<template>
  <div class="flow-node flow-node-gateway">
    <div class="gateway-content">
      <div class="node-icon">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
          <path
            d="M12 2L22 7L12 12L2 7L12 2Z"
            stroke="currentColor"
            stroke-width="2"
            fill="currentColor"
          />
          <path
            d="M2 17L12 22L22 17"
            stroke="currentColor"
            stroke-width="2"
            fill="none"
          />
          <path
            d="M2 12L12 17L22 12"
            stroke="currentColor"
            stroke-width="2"
            fill="none"
          />
        </svg>
      </div>
    </div>
    <Handle type="target" position="left" :style="{ background: '#f59e0b' }" />
    <Handle type="source" position="right" :style="{ background: '#f59e0b' }" />
  </div>
</template>

<script setup lang="ts">
import { Handle } from '@vue-flow/core';

defineProps<{
  data: {
    label: string;
    type: string;
    notes?: string;
  };
}>();
</script>

<style scoped>
.flow-node-gateway {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
  border: 2px solid #d97706;
  width: 100px;
  height: 100px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  transform: rotate(45deg);
  box-shadow: 0 4px 12px rgba(245, 158, 11, 0.3);
  transition: all 0.2s;
  position: relative;
  user-select: none;
  -webkit-user-drag: none;
}

.flow-node-gateway:hover {
  transform: rotate(45deg) scale(1.05);
  box-shadow: 0 6px 16px rgba(245, 158, 11, 0.4);
}

.gateway-content {
  transform: rotate(-45deg);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
}

.node-icon {
  color: #0f172a;
}
</style>

