<template>
  <div class="designer-page">
    <div class="designer-toolbar">
      <div class="toolbar-title">{{ currentProcessName || 'Flow Designer' }}</div>
      <div class="toolbar-actions">
        <button class="btn btn-primary" @click="handleExport" :disabled="!currentFlow">Export</button>
      </div>
    </div>

    <div class="designer-layout">
      <div class="panel panel-left">
        <FlowExplorer @process-selected="handleProcessSelected" />
      </div>

      <div class="panel panel-center">
        <FlowEditor 
          v-if="currentFlow && currentFlow.nodes && Array.isArray(currentFlow.nodes) && currentFlow.nodes.length > 0" 
          :flow="currentFlow" 
          @update:flow="handleFlowUpdate" 
        />
        <div v-else class="empty-diagram">
          <div class="empty-icon">📊</div>
          <div class="empty-text">{{ currentFlow ? 'Invalid flow format' : 'Select a flow process to view' }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, markRaw } from 'vue';
import FlowEditor from '~/src/components/FlowEditor.vue';
import FlowExplorer from '~/src/components/FlowExplorer.vue';
import type { FlowGraph } from '~/src/types/flowTypes';

interface ProcessSelectedData {
  path: string;
  name: string;
  flow: FlowGraph;
}

definePageMeta({
  layout: 'default'
});

const currentFlow = ref<FlowGraph | null>(null);
const currentProcessName = ref<string>('');

const handleProcessSelected = (data: ProcessSelectedData): void => {
  if (!data.flow) {
    console.error('[Designer] No flow in data:', data);
    return;
  }
  
  if (!data.flow.nodes || !Array.isArray(data.flow.nodes)) {
    console.error('[Designer] Invalid flow structure:', data.flow);
    alert(`Invalid flow format in ${data.name}. Nodes must be an array.`);
    return;
  }
  
  if (!data.flow.edges || !Array.isArray(data.flow.edges)) {
    data.flow.edges = [];
  }
  
  console.log('[Designer] Setting flow:', {
    nodeCount: data.flow.nodes.length,
    edgeCount: data.flow.edges.length
  });
  
  const normalizedFlow = JSON.parse(JSON.stringify(data.flow));
  currentFlow.value = markRaw(normalizedFlow) as FlowGraph;
  currentProcessName.value = data.name;
};

const handleFlowUpdate = (flow: FlowGraph): void => {
  const normalizedFlow = JSON.parse(JSON.stringify(flow));
  currentFlow.value = markRaw(normalizedFlow) as FlowGraph;
};

const handleExport = (): void => {
  if (!currentFlow.value) {
    alert('No flow loaded');
    return;
  }

  try {
    const jsonContent = JSON.stringify(currentFlow.value, null, 2);
    const blob = new Blob([jsonContent], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    let fileName = currentProcessName.value || 'process';
    fileName = fileName.replace(/\.vueflow\.json$/, '');
    link.href = url;
    link.download = `${fileName}.vueflow.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  } catch (error) {
    console.error('Failed to export:', error);
    alert('Failed to export flow. Please try again.');
  }
};
</script>

<style scoped>
.designer-page {
  height: 100%;
  width: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 1rem;
}

.designer-toolbar {
  background: rgba(11, 17, 32, 0.4);
  backdrop-filter: blur(10px);
  border-radius: 0.75rem;
  padding: 1rem 1.5rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.toolbar-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: #f9fafb;
}

.toolbar-actions {
  display: flex;
  gap: 0.75rem;
}

.btn {
  padding: 0.5rem 1.25rem;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
  outline: none;
}

.btn-primary {
  background: linear-gradient(135deg, #0ea5e9 0%, #22c55e 100%);
  color: #0f172a;
  font-weight: 600;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(14, 165, 233, 0.4);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.designer-layout {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 1rem;
  flex: 1;
  min-height: 0;
}

.panel {
  border-radius: 0.75rem;
  overflow: hidden;
  background: rgba(11, 17, 32, 0.3);
  backdrop-filter: blur(10px);
}

.panel-left {
  overflow-y: auto;
}

.panel-center {
  overflow: hidden;
  position: relative;
}

.empty-diagram {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #6b7280;
}

.empty-icon {
  font-size: 4rem;
  margin-bottom: 1rem;
  opacity: 0.5;
}

.empty-text {
  font-size: 1rem;
  opacity: 0.7;
}
</style>
