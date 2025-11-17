<template>
  <div class="flow-node flow-node-task" :class="categoryClass">
    <div class="node-header">
      <div class="node-icon-wrapper">
        <NodeIcon
          :icon="icon"
          :service="service"
          :category="category"
          :size="24"
        />
      </div>
      <div class="node-label">{{ data.label }}</div>
      <div v-if="serviceBadge" class="node-service-badge">{{ serviceBadge }}</div>
    </div>
    <div v-if="data.notes" class="node-notes" :title="data.notes">
      {{ data.notes }}
    </div>
    <div v-if="hasMetadata" class="node-metadata">
      <span v-if="category" class="metadata-tag">{{ category }}</span>
      <span v-if="endpoint" class="metadata-tag endpoint">{{ endpoint }}</span>
    </div>
    <Handle type="target" position="left" :style="{ background: handleColor }" />
    <Handle type="source" position="right" :style="{ background: handleColor }" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { Handle } from '@vue-flow/core';
import NodeIcon from '../icons/NodeIcon.vue';

const props = defineProps<{
  data: {
    label: string;
    type: string;
    notes?: string;
    rpa?: {
      metadata?: {
        icon?: string;
        category?: string;
        service?: string;
        endpoint?: string;
      };
    };
  };
}>();

const icon = computed(() => props.data.rpa?.metadata?.icon);
const category = computed(() => props.data.rpa?.metadata?.category);
const service = computed(() => props.data.rpa?.metadata?.service);
const endpoint = computed(() => props.data.rpa?.metadata?.endpoint);
const hasMetadata = computed(() => category.value || endpoint.value);

const serviceBadge = computed(() => {
  if (!service.value) return null;
  const serviceMap: Record<string, string> = {
    'airflow': 'AF',
    'rpa-api': 'API',
    'rpa-listener': 'LST',
    'rpa-robots': 'RBT',
  };
  return serviceMap[service.value] || service.value.toUpperCase().slice(0, 3);
});

const categoryClass = computed(() => {
  if (!category.value) return '';
  return `category-${category.value.replace(/_/g, '-')}`;
});

const handleColor = computed(() => {
  const categoryColors: Record<string, string> = {
    'data-input': '#3b82f6',
    'integration': '#8b5cf6',
    'api': '#0ea5e9',
    'messaging': '#ec4899',
    'orchestration': '#10b981',
    'webhook': '#f59e0b',
    'wait': '#6b7280',
    'storage': '#14b8a6',
    'callback': '#6366f1',
  };
  return categoryColors[category.value || ''] || '#4b5563';
});
</script>

<style scoped>
.flow-node-task {
  background: #1f2937;
  border: 2px solid #4b5563;
  border-radius: 12px;
  min-width: 220px;
  max-width: 280px;
  display: flex;
  flex-direction: column;
  padding: 0;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  transition: all 0.2s;
  overflow: hidden;
  user-select: none;
  -webkit-user-drag: none;
}

.flow-node-task:hover {
  border-color: #6b7280;
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.5);
  transform: translateY(-2px);
}

.node-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  background: rgba(31, 41, 55, 0.8);
  border-bottom: 1px solid rgba(75, 85, 99, 0.3);
}

.node-icon-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 28px;
  height: 28px;
}

.node-icon-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
}

.node-label {
  font-size: 13px;
  font-weight: 600;
  color: #f5f5f5;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.node-service-badge {
  font-size: 9px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 4px;
  background: rgba(14, 165, 233, 0.2);
  color: #0ea5e9;
  border: 1px solid rgba(14, 165, 233, 0.3);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.node-notes {
  font-size: 11px;
  color: #9ca3af;
  padding: 8px 14px;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  background: rgba(15, 23, 42, 0.5);
}

.node-metadata {
  display: flex;
  gap: 6px;
  padding: 8px 14px;
  flex-wrap: wrap;
  background: rgba(15, 23, 42, 0.3);
  border-top: 1px solid rgba(75, 85, 99, 0.2);
}

.metadata-tag {
  font-size: 10px;
  padding: 3px 8px;
  border-radius: 4px;
  background: rgba(75, 85, 99, 0.4);
  color: #d1d5db;
  border: 1px solid rgba(75, 85, 99, 0.5);
}

.metadata-tag.endpoint {
  font-family: 'Courier New', monospace;
  background: rgba(14, 165, 233, 0.15);
  color: #7dd3fc;
  border-color: rgba(14, 165, 233, 0.3);
}

/* Category-specific styling */
.category-data-input {
  border-left: 4px solid #3b82f6;
}

.category-integration {
  border-left: 4px solid #8b5cf6;
}

.category-api {
  border-left: 4px solid #0ea5e9;
}

.category-messaging {
  border-left: 4px solid #ec4899;
}

.category-orchestration {
  border-left: 4px solid #10b981;
}

.category-webhook {
  border-left: 4px solid #f59e0b;
}

.category-wait {
  border-left: 4px solid #6b7280;
}

.category-storage {
  border-left: 4px solid #14b8a6;
}

.category-callback {
  border-left: 4px solid #6366f1;
}
</style>

