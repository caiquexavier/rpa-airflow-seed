/**
 * Vueflow-compatible flow types
 * Direct mapping to Vueflow JSON format
 */

export interface FlowNode {
  id: string;
  type: string;
  position: { x: number; y: number };
  data: {
    label: string;
    type: string;
    notes?: string;
    steps?: FlowNode[]; // For subprocess nodes
    rpa?: Record<string, any>;
    [key: string]: any; // Allow additional custom fields
  };
  draggable?: boolean;
  selectable?: boolean;
  connectable?: boolean;
}

export interface FlowEdge {
  id: string;
  source: string;
  target: string;
  type?: string;
  label?: string;
  [key: string]: any; // Allow additional custom fields
}

export interface FlowGraph {
  nodes: FlowNode[];
  edges: FlowEdge[];
}

export interface FlowProcess {
  process_id: string;
  title: string;
  description?: string;
  flow: FlowGraph;
}

