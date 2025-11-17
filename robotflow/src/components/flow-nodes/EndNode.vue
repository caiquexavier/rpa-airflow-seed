<template>
  <div class="flow-node flow-node-end">
    <div class="node-icon">
      <svg width="32" height="32" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="12" cy="12" r="10" fill="currentColor" />
        <rect x="8" y="8" width="8" height="8" rx="1.5" fill="#0f172a" />
      </svg>
    </div>
    <Handle type="target" position="left" :style="{ background: '#ef4444' }" />
  </div>
</template>

<script setup lang="ts">
import { Handle } from '@vue-flow/core';

defineProps<{
  data: {
    label?: string;
    type: string;
    notes?: string;
  };
}>();
</script>

<style scoped>
.flow-node-end {
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
  border: 2px solid #dc2626;
  border-radius: 50%;
  width: 80px;
  height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3);
  transition: all 0.2s;
  user-select: none;
  -webkit-user-drag: none;
}

.flow-node-end:hover {
  transform: scale(1.05);
  box-shadow: 0 6px 16px rgba(239, 68, 68, 0.4);
}

.node-icon {
  color: #0f172a;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
