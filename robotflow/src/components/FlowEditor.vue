<template>
  <div class="flow-editor">
    <VueFlow
      ref="vueFlowInstance"
      v-model:nodes="nodes"
      v-model:edges="edges"
      :node-types="nodeTypes"
      :default-edge-options="defaultEdgeOptions"
      :fit-view-on-init="true"
      :min-zoom="0.1"
      :max-zoom="3"
      :snap-to-grid="true"
      :snap-grid="[20, 20]"
      :nodes-draggable="true"
      :nodes-connectable="true"
      :elements-selectable="true"
      :pan-on-drag="[1, 2]"
      :pan-on-scroll="false"
      :zoom-on-scroll="true"
      :zoom-on-pinch="true"
      :pan-on-drag-mode="'free'"
      :select-nodes-on-drag="false"
      :delete-key-code="'Delete'"
      :multi-select-key-code="'Shift'"
      :connection-mode="'loose'"
      :auto-pan-on-node-drag="true"
      :auto-pan-on-connect="true"
      :prevent-scrolling="true"
      class="vue-flow-container"
      @nodes-change="onNodesChange"
      @edges-change="onEdgesChange"
      @connect="onConnect"
      @pane-ready="handlePaneReady"
      @node-drag-stop="onNodeDragStop"
    >
      <Background pattern-color="#374151" :gap="20" />
      <Controls :show-lock="false" />
      <MiniMap 
        :width="150"
        :height="100"
        node-stroke-color="#0ea5e9"
        node-color="#1f2937"
        mask-color="rgba(15, 23, 42, 0.6)"
      />
    </VueFlow>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, markRaw, nextTick } from 'vue';
import { VueFlow } from '@vue-flow/core';
import { Background } from '@vue-flow/background';
import { Controls } from '@vue-flow/controls';
import { MiniMap } from '@vue-flow/minimap';
import '@vue-flow/core/dist/style.css';
import '@vue-flow/core/dist/theme-default.css';
import '@vue-flow/minimap/dist/style.css';
import type { FlowGraph, FlowNode, FlowEdge } from '~/src/types/flowTypes';
import { applyAutoLayout } from '~/src/utils/autoLayout';
import StartNode from './flow-nodes/StartNode.vue';
import EndNode from './flow-nodes/EndNode.vue';
import TaskNode from './flow-nodes/TaskNode.vue';
import GatewayNode from './flow-nodes/GatewayNode.vue';
import SubprocessNode from './flow-nodes/SubprocessNode.vue';

const props = defineProps<{
  flow: FlowGraph;
}>();

const emit = defineEmits<{
  (e: 'update:flow', flow: FlowGraph): void;
  (e: 'save', flow: FlowGraph): void;
}>();

const nodeTypes = {
  start: markRaw(StartNode),
  end: markRaw(EndNode),
  task: markRaw(TaskNode),
  gateway: markRaw(GatewayNode),
  subprocess: markRaw(SubprocessNode),
};

const defaultEdgeOptions = {
  type: 'straight', // Only horizontal/vertical arrows, NO ANGLES PROHIBITED
  animated: false,
  style: { stroke: '#6b7280', strokeWidth: 2.5 },
  markerEnd: {
    type: 'arrowclosed',
    color: '#6b7280',
    width: 18,
    height: 18,
  },
};

const nodes = ref<FlowNode[]>([]);
const edges = ref<FlowEdge[]>([]);
const vueFlowInstance = ref<InstanceType<typeof VueFlow> | null>(null);

const updateFromFlow = async (): Promise<void> => {
  if (!props.flow) {
    console.warn('[FlowEditor] No flow provided');
    return;
  }
  
  try {
    const safeFlow = JSON.parse(JSON.stringify(props.flow));
    
    if (!safeFlow.nodes || !Array.isArray(safeFlow.nodes)) {
      console.error('[FlowEditor] Invalid flow structure: nodes must be an array');
      nodes.value = [];
      edges.value = [];
      return;
    }
    
    if (!safeFlow.edges || !Array.isArray(safeFlow.edges)) {
      console.warn('[FlowEditor] Flow missing edges array, using empty array');
      safeFlow.edges = [];
    }
    
    // Apply auto-layout to nodes and edges
    const { nodes: layoutedNodes, edges: optimizedEdges } = applyAutoLayout(safeFlow.nodes, safeFlow.edges);
    
    nodes.value = layoutedNodes;
    // Force edge types to ensure horizontal/vertical only (especially for start/end nodes)
    edges.value = optimizedEdges.map(edge => {
      const sourceNode = layoutedNodes.find(n => n.id === edge.source);
      const targetNode = layoutedNodes.find(n => n.id === edge.target);
      
      if (!sourceNode || !targetNode) {
        return { ...edge, type: 'straight' };
      }
      
      // Check if nodes are in the same row
      const rowThreshold = 10;
      const sameRow = Math.abs(sourceNode.position.y - targetNode.position.y) < rowThreshold;
      
      // Force correct edge type - especially for start and end nodes
      return {
        ...edge,
        type: sameRow ? 'straight' : 'step', // Horizontal/vertical only, no angles
      };
    });
    
    await nextTick();
    autoAlignNodes();
  } catch (error) {
    console.error('[FlowEditor] Error updating from flow:', error);
    nodes.value = [];
    edges.value = [];
  }
};

const handlePaneReady = (): void => {
  autoAlignNodes();
};

const autoAlignNodes = (): void => {
  if (!nodes.value || nodes.value.length === 0) return;
  
  nextTick(() => {
    try {
      const instance = vueFlowInstance.value as any;
      if (instance?.fitView && typeof instance.fitView === 'function') {
        // Fit view with proper padding to show all nodes and edges
        instance.fitView({ 
          padding: 0.15, 
          duration: 500,
          includeHiddenNodes: false,
          minZoom: 0.2,
          maxZoom: 1.2
        });
      }
    } catch (error) {
      console.warn('Could not auto-align nodes:', error);
    }
  });
};

const onNodeDragStop = (): void => {
  nextTick(() => {
    // Re-validate all edges after node drag to ensure horizontal/vertical only
    emitUpdate();
  });
};

const onNodesChange = (changes: any[]): void => {
  const isDragging = changes.some((change: any) => change.dragging === true);
  
  if (!isDragging) {
    // Re-validate edges when nodes change position to ensure horizontal/vertical only
    emitUpdate();
  }
};

const onEdgesChange = (): void => {
  emitUpdate();
};

const onConnect = (connection: { source: string; target: string }): void => {
  // STRICT ENFORCEMENT: Only horizontal or vertical arrows, NO ANGLES PROHIBITED
  const sourceNode = nodes.value.find(n => n.id === connection.source);
  const targetNode = nodes.value.find(n => n.id === connection.target);
  
  // Check if nodes are in the same row (same Y position within threshold)
  const rowThreshold = 10; // Allow small tolerance for alignment
  const sameRow = sourceNode && targetNode && 
    Math.abs(sourceNode.position.y - targetNode.position.y) < rowThreshold;
  
  // STRICT RULE: Only 'straight' (horizontal) or 'step' (horizontal then vertical)
  // NEVER use edge types that create angles (smoothstep, bezier, etc.)
  const edgeType = sameRow ? 'straight' : 'step'; // Both enforce horizontal/vertical only
  
  const newEdge: FlowEdge = {
    id: `${connection.source}->${connection.target}`,
    source: connection.source,
    target: connection.target,
    type: edgeType, // Only 'straight' or 'step' - NO ANGLES ALLOWED
  };
  edges.value.push(newEdge);
  emitUpdate();
};

const emitUpdate = (): void => {
  if (nodes.value.length === 0) return;

  // Ensure all edges use only horizontal/vertical (no angles)
  // Force edge types for start, end, gateway, task, subprocess connections
  // SPECIAL: Start and End nodes MUST use horizontal/vertical only
  const validatedEdges = edges.value.map(edge => {
    const sourceNode = nodes.value.find(n => n.id === edge.source);
    const targetNode = nodes.value.find(n => n.id === edge.target);
    
    if (!sourceNode || !targetNode) {
      return { ...edge, type: 'straight' }; // Default to horizontal
    }
    
    // Check if source or target is start/end node
    const isStartNode = sourceNode.type === 'start';
    const isEndNode = targetNode.type === 'end';
    
    // Check if nodes are in the same row
    const rowThreshold = 10;
    const sameRow = Math.abs(sourceNode.position.y - targetNode.position.y) < rowThreshold;
    
    // Force correct edge type - override any existing type
    // Same row: straight (horizontal only)
    // Different rows: step (horizontal then vertical)
    // This applies to ALL nodes including start and end
    const edgeType = sameRow ? 'straight' : 'step';
    
    // Create clean edge with only necessary properties
    const cleanEdge: FlowEdge = {
      id: edge.id,
      source: edge.source,
      target: edge.target,
      type: edgeType, // Force horizontal/vertical only, no angles
    };
    
    // Preserve label if exists
    if (edge.label) {
      cleanEdge.label = edge.label;
    }
    
    return cleanEdge;
  });

  const flow: FlowGraph = {
    nodes: nodes.value,
    edges: validatedEdges,
  };

  emit('update:flow', flow);
};

const save = (): void => {
  if (nodes.value.length === 0) return;

  const flow: FlowGraph = {
    nodes: nodes.value,
    edges: edges.value,
  };

  emit('save', flow);
};

watch(() => props.flow, () => {
  nextTick(() => {
    updateFromFlow();
  });
}, { deep: true });

onMounted(() => {
  updateFromFlow();
});

defineExpose({
  save,
  autoAlign: autoAlignNodes,
});
</script>

<style scoped>
.flow-editor {
  width: 100%;
  height: 100%;
  position: relative;
  background: #0f172a;
}

.vue-flow-container {
  width: 100%;
  height: 100%;
}

:deep(.vue-flow__node) {
  cursor: grab;
  transition: transform 0.2s, box-shadow 0.2s;
  pointer-events: all;
  user-select: none;
}

:deep(.vue-flow__node:active) {
  cursor: grabbing;
}

:deep(.vue-flow__node.draggable) {
  cursor: grab;
}

:deep(.vue-flow__node.draggable.dragging) {
  cursor: grabbing;
}

:deep(.vue-flow__node.dragging) {
  opacity: 0.8;
  transform: scale(1.05);
  z-index: 1000;
  box-shadow: 0 8px 24px rgba(14, 165, 233, 0.4);
}

:deep(.vue-flow__node.selected) {
  outline: 2px solid #0ea5e9;
  outline-offset: 2px;
}

:deep(.vue-flow__edge) {
  cursor: pointer;
}

:deep(.vue-flow__edge-path) {
  stroke: #6b7280;
  stroke-width: 2.5;
  transition: all 0.2s;
  fill: none;
  /* Force horizontal/vertical only - no curves or angles */
  vector-effect: non-scaling-stroke;
}

/* Force step edges to be strictly horizontal/vertical */
:deep(.vue-flow__edge[data-type="step"] .vue-flow__edge-path) {
  /* Ensure step edges use only horizontal and vertical segments */
  stroke-linecap: square;
}

/* Force straight edges to be strictly horizontal */
:deep(.vue-flow__edge[data-type="straight"] .vue-flow__edge-path) {
  /* Ensure straight edges are perfectly horizontal */
  stroke-linecap: square;
}

:deep(.vue-flow__edge-marker) {
  fill: #6b7280;
}

:deep(.vue-flow__edge:hover .vue-flow__edge-path) {
  stroke: #0ea5e9;
  stroke-width: 3;
  filter: drop-shadow(0 0 4px rgba(14, 165, 233, 0.5));
}

:deep(.vue-flow__edge:hover .vue-flow__edge-marker) {
  fill: #0ea5e9;
}

:deep(.vue-flow__edge.selected .vue-flow__edge-path) {
  stroke: #0ea5e9;
  stroke-width: 3;
  filter: drop-shadow(0 0 4px rgba(14, 165, 233, 0.5));
}

:deep(.vue-flow__edge.selected .vue-flow__edge-text) {
  fill: #0ea5e9;
  font-weight: 600;
}

:deep(.vue-flow__connection-line) {
  stroke: #0ea5e9;
  stroke-width: 2;
}

:deep(.vue-flow__handle) {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: 2px solid #0f172a;
  background: #4b5563;
  transition: all 0.2s;
}

:deep(.vue-flow__handle:hover) {
  transform: scale(1.3);
  border-color: #0ea5e9;
  box-shadow: 0 0 8px rgba(14, 165, 233, 0.6);
}

:deep(.vue-flow__handle.connecting) {
  background: #0ea5e9;
  border-color: #0ea5e9;
  box-shadow: 0 0 12px rgba(14, 165, 233, 0.8);
}

:deep(.vue-flow__controls) {
  background: rgba(15, 23, 42, 0.9);
  border: 1px solid rgba(75, 85, 99, 0.3);
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 4px;
}

:deep(.vue-flow__controls-button) {
  background: rgba(31, 41, 55, 0.8);
  border: 1px solid rgba(75, 85, 99, 0.3);
  color: #ffffff !important;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
}

:deep(.vue-flow__controls-button svg) {
  width: 14px !important;
  height: 14px !important;
  color: #ffffff !important;
  fill: #ffffff !important;
  stroke: #ffffff !important;
}

:deep(.vue-flow__controls-button path) {
  stroke: #ffffff !important;
  fill: #ffffff !important;
}

:deep(.vue-flow__controls-button:hover) {
  background: rgba(55, 65, 81, 0.9);
  border-color: #0ea5e9;
  color: #ffffff !important;
}

:deep(.vue-flow__controls-button:hover svg) {
  color: #ffffff !important;
  fill: #ffffff !important;
  stroke: #ffffff !important;
}

:deep(.vue-flow__controls-button:hover path) {
  stroke: #ffffff !important;
  fill: #ffffff !important;
}

/* Hide lock button */
:deep(.vue-flow__controls-button[aria-label*="lock" i]),
:deep(.vue-flow__controls-button[aria-label*="Lock" i]),
:deep(.vue-flow__controls-button[title*="lock" i]),
:deep(.vue-flow__controls-button[title*="Lock" i]) {
  display: none !important;
}

:deep(.vue-flow__controls-button:active) {
  transform: scale(0.95);
  background: rgba(14, 165, 233, 0.2);
}

:deep(.vue-flow__minimap) {
  background: rgba(15, 23, 42, 0.9);
  border: 1px solid rgba(75, 85, 99, 0.3);
  border-radius: 8px;
  width: 150px !important;
  height: 100px !important;
  min-width: 150px !important;
  min-height: 100px !important;
  max-width: 150px !important;
  max-height: 100px !important;
}

:deep(.vue-flow__minimap-mask) {
  fill: rgba(15, 23, 42, 0.6);
}

:deep(.vue-flow__minimap-node) {
  fill: #1f2937;
  stroke: #0ea5e9;
  stroke-width: 1;
}

:deep(.vue-flow__background) {
  opacity: 0.3;
}

:deep(.vue-flow__pane) {
  cursor: default;
}

:deep(.vue-flow__pane.dragging) {
  cursor: grabbing;
}

:deep(.vue-flow__node-wrapper) {
  pointer-events: all;
  cursor: grab;
}

:deep(.vue-flow__node) {
  touch-action: none;
  cursor: grab;
}

:deep(.vue-flow__node.dragging) {
  cursor: grabbing !important;
}

:deep(.vue-flow__handle) {
  pointer-events: all;
  cursor: crosshair;
}

:deep(.vue-flow__controls-button) {
  transition: all 0.2s;
}

:deep(.vue-flow__controls-button:active) {
  transform: scale(0.95);
}

:deep(.vue-flow__selection) {
  background: rgba(14, 165, 233, 0.1);
  border: 1px solid #0ea5e9;
}

:deep(.vue-flow__connection-line) {
  stroke-dasharray: 5 5;
  animation: dash 0.5s linear infinite;
}

@keyframes dash {
  to {
    stroke-dashoffset: -10;
  }
}
</style>

