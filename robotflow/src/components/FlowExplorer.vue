<template>
  <div class="flow-explorer">
    <div class="explorer-header">
      <div class="explorer-title">
        <svg class="explorer-icon" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M3 6C3 4.89543 3.89543 4 5 4H9.58579C9.851 4 10.1054 4.10536 10.2929 4.29289L12.7071 6.70711C12.8946 6.89464 13.149 7 13.4142 7H19C20.1046 7 21 7.89543 21 9V18C21 19.1046 20.1046 20 19 20H5C3.89543 20 3 19.1046 3 18V6Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        <span>Flow Processes</span>
      </div>
      <button 
        class="btn-refresh" 
        :class="{ 'refreshing': loading }"
        @click="handleRefresh" 
        :disabled="loading"
        title="Refresh (F5)"
      >
        <svg class="refresh-icon" :class="{ 'spinning': loading }" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M1 4V10H7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          <path d="M23 20V14H17" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          <path d="M20.49 9A9 9 0 0 0 5.64 5.64L1 10M23 14L18.36 18.36A9 9 0 0 1 3.51 15" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </button>
    </div>
    <div class="explorer-content">
      <div v-if="loading" class="explorer-loading">
        <svg class="loading-spinner" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-dasharray="31.416" stroke-dashoffset="31.416" opacity="0.3"/>
          <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-dasharray="31.416" stroke-dashoffset="23.562" opacity="0.7"/>
        </svg>
        <span>Loading...</span>
      </div>
      <div v-else-if="error" class="explorer-error">
        <svg class="error-icon" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/>
          <path d="M12 8V12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
          <path d="M12 16H12.01" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        </svg>
        <span class="error-message">{{ error }}</span>
        <button class="btn-retry" @click="handleRefresh">Retry</button>
      </div>
      <div v-else-if="files.length === 0" class="explorer-empty">
        <svg class="empty-icon" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M14 2H6C5.46957 2 4.96086 2.21071 4.58579 2.58579C4.21071 2.96086 4 3.46957 4 4V20C4 20.5304 4.21071 21.0391 4.58579 21.4142C4.96086 21.7893 5.46957 22 6 22H18C18.5304 22 19.0391 21.7893 19.4142 21.4142C19.7893 21.0391 20 20.5304 20 20V8L14 2Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          <path d="M14 2V8H20" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          <path d="M12 18V12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          <path d="M9 15H15" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        <span>No flow processes found</span>
      </div>
      <div v-else class="file-list">
        <div
          v-for="file in files"
          :key="file.path"
          class="file-item"
          :class="{ active: selectedFile === file.path }"
          @click="selectFile(file)"
        >
          <svg class="file-icon" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M14 2H6C5.46957 2 4.96086 2.21071 4.58579 2.58579C4.21071 2.96086 4 3.46957 4 4V20C4 20.5304 4.21071 21.0391 4.58579 21.4142C4.96086 21.7893 5.46957 22 6 22H18C18.5304 22 19.0391 21.7893 19.4142 21.4142C19.7893 21.0391 20 20.5304 20 20V8L14 2Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M14 2V8H20" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M16 13H8" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M16 17H8" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M10 9H9H8" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          <span class="file-name">{{ file.name }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
import type { FlowGraph } from '~/src/types/flowTypes';

interface FlowFile {
  name: string;
  path: string;
}

interface ProcessSelectedEvent {
  path: string;
  name: string;
  flow: FlowGraph;
}

const emit = defineEmits<{
  (e: 'process-selected', data: ProcessSelectedEvent): void;
}>();

const files = ref<FlowFile[]>([]);
const loading = ref(false);
const selectedFile = ref<string | null>(null);
const error = ref<string | null>(null);

const loadFiles = async (force = false): Promise<void> => {
  if (loading.value && !force) return;
  
  loading.value = true;
  error.value = null;
  try {
    const response = await $fetch<FlowFile[]>('/api/flow/list', {
      method: 'GET',
      query: { _t: Date.now() }
    });
    files.value = response || [];
    error.value = null;
  } catch (err) {
    console.error('[FlowExplorer] Failed to load flow files:', err);
    let errorMessage = 'Failed to load flow files';
    
    if (err instanceof Error) {
      errorMessage = err.message;
    }
    
    if (err && typeof err === 'object' && 'data' in err) {
      const errorData = err.data as { error?: string };
      if (errorData?.error) {
        errorMessage = errorData.error;
      }
    }
    
    if (err && typeof err === 'object' && 'statusCode' in err) {
      const statusCode = err.statusCode as number;
      if (statusCode === 500) {
        errorMessage = 'Server error: Could not read process files. Check server logs.';
      } else if (statusCode === 404) {
        errorMessage = 'API endpoint not found. Is the server running?';
      }
    }
    
    error.value = errorMessage;
    files.value = [];
  } finally {
    loading.value = false;
  }
};

const handleRefresh = async (): Promise<void> => {
  await loadFiles(true);
};

const selectFile = async (file: FlowFile): Promise<void> => {
  selectedFile.value = file.path;
  try {
    const apiPath = `/api/flow/${file.name}`;
    const response = await fetch(apiPath);
    
    if (!response.ok) {
      const errorText = await response.text().catch(() => 'Unknown error');
      throw new Error(`HTTP ${response.status}: ${errorText}`);
    }
    
    const jsonData = await response.json();
    
    if (!jsonData || typeof jsonData !== 'object') {
      throw new Error('Invalid JSON format');
    }
    
    // Validate it's a FlowGraph
    if (!jsonData.nodes || !Array.isArray(jsonData.nodes)) {
      throw new Error('Invalid flow format: nodes must be an array');
    }
    
    if (!jsonData.edges || !Array.isArray(jsonData.edges)) {
      // Edges are optional, but if present should be an array
      jsonData.edges = [];
    }
    
    const flow: FlowGraph = {
      nodes: jsonData.nodes,
      edges: jsonData.edges,
    };
    
    emit('process-selected', { path: file.path, name: file.name, flow });
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    console.error('[FlowExplorer] Failed to load process:', {
      file: file.name,
      error: errorMessage,
    });
    alert(`Failed to load ${file.name}: ${errorMessage}`);
  }
};

const handleKeyPress = (event: KeyboardEvent): void => {
  if (event.key === 'F5' || (event.ctrlKey && event.key === 'r')) {
    event.preventDefault();
    handleRefresh();
  }
};

onMounted(() => {
  loadFiles();
  window.addEventListener('keydown', handleKeyPress);
});

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyPress);
});
</script>

<style scoped>
.flow-explorer {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: transparent;
}

.explorer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  border-bottom: none;
}

.explorer-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 600;
  color: #f9fafb;
  font-size: 0.875rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.explorer-icon {
  width: 1.25rem;
  height: 1.25rem;
  color: #0ea5e9;
  flex-shrink: 0;
}

.btn-refresh {
  background: transparent;
  border: none;
  color: #9ca3af;
  cursor: pointer;
  padding: 0.375rem;
  border-radius: 0.375rem;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 2rem;
  min-height: 2rem;
}

.btn-refresh svg {
  width: 1.125rem;
  height: 1.125rem;
}

.btn-refresh:hover:not(:disabled) {
  background: rgba(75, 85, 99, 0.2);
  color: #f9fafb;
}

.btn-refresh:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.btn-refresh.refreshing {
  color: #0ea5e9;
}

.refresh-icon {
  display: inline-block;
  transition: transform 0.2s;
}

.refresh-icon.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.explorer-content {
  flex: 1;
  overflow-y: auto;
  padding: 0.5rem;
}

.explorer-loading {
  padding: 2rem 1rem;
  text-align: center;
  color: #6b7280;
  font-size: 0.875rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
}

.loading-spinner {
  width: 2rem;
  height: 2rem;
  color: #0ea5e9;
  animation: spin 1s linear infinite;
}

.explorer-error {
  padding: 2rem 1rem;
  text-align: center;
  color: #ef4444;
  font-size: 0.875rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
}

.error-icon {
  width: 3rem;
  height: 3rem;
  color: #ef4444;
  opacity: 0.8;
}

.error-message {
  color: #fca5a5;
  max-width: 100%;
  word-wrap: break-word;
}

.btn-retry {
  margin-top: 0.5rem;
  padding: 0.5rem 1rem;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 0.375rem;
  color: #fca5a5;
  cursor: pointer;
  font-size: 0.875rem;
  transition: all 0.2s;
}

.btn-retry:hover {
  background: rgba(239, 68, 68, 0.2);
  border-color: rgba(239, 68, 68, 0.5);
  color: #f87171;
}

.explorer-empty {
  padding: 2rem 1rem;
  text-align: center;
  color: #6b7280;
  font-size: 0.875rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
}

.empty-icon {
  width: 3rem;
  height: 3rem;
  color: #4b5563;
  opacity: 0.5;
}

.file-list {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  border-radius: 0.5rem;
  cursor: pointer;
  transition: all 0.2s;
  color: #d1d5db;
  font-size: 0.875rem;
}

.file-item:hover {
  background: rgba(75, 85, 99, 0.2);
  color: #f9fafb;
}

.file-item.active {
  background: rgba(14, 165, 233, 0.15);
  color: #0ea5e9;
}

.file-icon {
  width: 1.125rem;
  height: 1.125rem;
  color: #9ca3af;
  flex-shrink: 0;
  transition: color 0.2s;
}

.file-item:hover .file-icon {
  color: #0ea5e9;
}

.file-item.active .file-icon {
  color: #0ea5e9;
}

.file-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.explorer-content::-webkit-scrollbar {
  width: 6px;
}

.explorer-content::-webkit-scrollbar-track {
  background: rgba(17, 24, 39, 0.5);
  border-radius: 3px;
}

.explorer-content::-webkit-scrollbar-thumb {
  background: rgba(75, 85, 99, 0.5);
  border-radius: 3px;
}

.explorer-content::-webkit-scrollbar-thumb:hover {
  background: rgba(75, 85, 99, 0.7);
}
</style>

