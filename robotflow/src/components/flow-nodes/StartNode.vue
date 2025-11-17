<template>
  <div class="flow-node flow-node-start">
    <div class="node-icon">
      <svg width="32" height="32" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="12" cy="12" r="10" fill="currentColor" />
        <path d="M9 8L15 12L9 16V8Z" fill="#0f172a" />
      </svg>
    </div>
    <Handle type="source" position="right" :style="{ background: '#22c55e' }" />
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
.flow-node-start {
  background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);
  border: 2px solid #16a34a;
  border-radius: 50%;
  width: 80px;
  height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 12px rgba(34, 197, 94, 0.3);
  transition: all 0.2s;
  user-select: none;
  -webkit-user-drag: none;
}

.flow-node-start:hover {
  transform: scale(1.05);
  box-shadow: 0 6px 16px rgba(34, 197, 94, 0.4);
}

.node-icon {
  color: #0f172a;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
