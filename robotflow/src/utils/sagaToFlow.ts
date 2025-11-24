/**
 * Utility to convert SAGA objects to Vue Flow JSON format
 */

import type { FlowGraph, FlowNode, FlowEdge } from '~/src/types/flowTypes';
import { applyAutoLayout } from './autoLayout';

interface SagaEvent {
  event_type: string;
  event_data: Record<string, any>;
  task_id?: string;
  dag_id?: string;
  dag_run_id?: string;
  execution_date?: string;
  try_number?: number;
  operator_type?: string;
  operator_id?: string;
  operator_params?: Record<string, any>;
  occurred_at?: string;
}

interface Saga {
  saga_id: number;
  rpa_key_id: string;
  data: Record<string, any>;
  current_state: string;
  events: SagaEvent[];
  events_count: number;
  created_at: string | null;
  updated_at: string | null;
}

/**
 * Determine event status from event type and saga state
 * Event Sourcing pattern: each event has a status
 */
function determineEventStatus(event: SagaEvent, sagaState: string, eventIndex: number, totalEvents: number): {
  status: string;
  statusColor: string;
  statusIcon: string;
} {
  const eventType = event.event_type || '';
  
  // Determine status based on event type
  if (eventType.includes('Start') || eventType.includes('Created')) {
    return {
      status: 'STARTED',
      statusColor: '#22c55e',
      statusIcon: '▶️',
    };
  }
  
  if (eventType.includes('Complete') || eventType.includes('Completed') || eventType.includes('Success')) {
    return {
      status: 'COMPLETED',
      statusColor: '#10b981',
      statusIcon: '✅',
    };
  }
  
  if (eventType.includes('Failed') || eventType.includes('Error') || eventType.includes('Exception')) {
    return {
      status: 'FAILED',
      statusColor: '#ef4444',
      statusIcon: '❌',
    };
  }
  
  if (eventType.includes('Compensat') || eventType.includes('Rollback')) {
    return {
      status: 'COMPENSATING',
      statusColor: '#f59e0b',
      statusIcon: '↩️',
    };
  }
  
  if (eventType.includes('Running') || eventType.includes('InProgress')) {
    return {
      status: 'RUNNING',
      statusColor: '#0ea5e9',
      statusIcon: '⏳',
    };
  }
  
  // Check if this is the last event and saga is completed
  if (eventIndex === totalEvents - 1 && sagaState === 'COMPLETED') {
    return {
      status: 'COMPLETED',
      statusColor: '#10b981',
      statusIcon: '✅',
    };
  }
  
  // Default status based on saga state
  if (sagaState === 'FAILED') {
    return {
      status: 'FAILED',
      statusColor: '#ef4444',
      statusIcon: '❌',
    };
  }
  
  if (sagaState === 'COMPENSATING') {
    return {
      status: 'COMPENSATING',
      statusColor: '#f59e0b',
      statusIcon: '↩️',
    };
  }
  
  // Default: pending or running
  return {
    status: 'PENDING',
    statusColor: '#6b7280',
    statusIcon: '⏸️',
  };
}

/**
 * Determine category based on operator type and event data
 */
function determineCategory(event: SagaEvent): string {
  const operatorType = event.operator_type || '';
  const eventData = event.event_data || {};
  
  if (operatorType.includes('Robot')) {
    return 'orchestration';
  }
  if (operatorType.includes('Python')) {
    return 'integration';
  }
  if (eventData.endpoint || eventData.url) {
    return 'api';
  }
  if (eventData.queue || eventData.exchange) {
    return 'messaging';
  }
  if (eventData.webhook || eventData.callback) {
    return 'webhook';
  }
  if (eventData.database || eventData.query) {
    return 'storage';
  }
  
  return 'orchestration';
}

/**
 * Determine service based on operator type
 */
function determineService(event: SagaEvent): string {
  const operatorType = event.operator_type || '';
  
  if (operatorType.includes('Robot')) {
    return 'rpa-robots';
  }
  if (operatorType.includes('Python')) {
    return 'airflow';
  }
  
  return 'rpa-api';
}

/**
 * Get icon based on category and operator type
 */
function getIcon(category: string, operatorType: string): string {
  const iconMap: Record<string, string> = {
    'orchestration': '⚙️',
    'integration': '🔗',
    'api': '🌐',
    'messaging': '📨',
    'webhook': '🔔',
    'storage': '💾',
    'data-input': '📥',
    'callback': '↩️',
  };
  
  return iconMap[category] || '📋';
}

/**
 * Build detailed notes from event data for Event Sourcing visualization
 */
function buildEventDetails(event: SagaEvent, eventIndex: number): string {
  const details: string[] = [];
  
  // Event sequence number
  details.push(`#${eventIndex + 1}`);
  
  // Event type (main identifier)
  if (event.event_type) {
    details.push(event.event_type);
  }
  
  // Task/DAG context
  if (event.task_id) {
    details.push(`Task: ${event.task_id}`);
  }
  if (event.dag_id) {
    details.push(`DAG: ${event.dag_id}`);
  }
  
  // Timestamp
  if (event.occurred_at) {
    const date = new Date(event.occurred_at);
    const timeStr = date.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
    details.push(`@ ${timeStr}`);
  }
  
  return details.join(' • ');
}

/**
 * Build extended notes with more details
 */
function buildExtendedNotes(event: SagaEvent): string {
  const notes: string[] = [];
  
  // Operator information
  if (event.operator_type) {
    notes.push(`Operator: ${event.operator_type}`);
  }
  
  // Try number if retry
  if (event.try_number && event.try_number > 1) {
    notes.push(`Try: ${event.try_number}`);
  }
  
  // Execution date
  if (event.execution_date) {
    const execDate = new Date(event.execution_date);
    notes.push(`Exec: ${execDate.toLocaleString()}`);
  }
  
  // Event data keys
  if (event.event_data && Object.keys(event.event_data).length > 0) {
    const dataKeys = Object.keys(event.event_data).slice(0, 3).join(', ');
    notes.push(`Data: ${dataKeys}`);
  }
  
  // Operator params
  if (event.operator_params && Object.keys(event.operator_params).length > 0) {
    const paramKeys = Object.keys(event.operator_params).slice(0, 2).join(', ');
    notes.push(`Params: ${paramKeys}`);
  }
  
  return notes.join(' | ');
}

/**
 * Convert SAGA object to Vue Flow JSON format
 * 
 * Event Sourcing pattern: Every event is a box (node) with status and details.
 * CQRS pattern: Events represent commands/queries in the saga.
 * SAGA pattern: Events show the orchestration flow.
 * 
 * All events are shown as task nodes (no BPMN-style start/end/gateway).
 * Each event box shows:
 * - Event status (STARTED, COMPLETED, FAILED, COMPENSATING, RUNNING, PENDING)
 * - Event details (type, task, timestamp, data)
 * - Full event information
 */
export function sagaToFlow(saga: Saga): FlowGraph {
  const nodes: FlowNode[] = [];
  const edges: FlowEdge[] = [];
  
  if (!saga.events || saga.events.length === 0) {
    return { nodes, edges };
  }
  
  const totalEvents = saga.events.length;
  
  // Create nodes for EVERY event (Event Sourcing: all events are important)
  saga.events.forEach((event, index) => {
    // Determine event status
    const eventStatus = determineEventStatus(event, saga.current_state, index, totalEvents);
    
    // Create unique node ID from event index
    const nodeId = `saga-${saga.saga_id}-event-${index}`;
    
    // Determine label from event (prioritize event_type for Event Sourcing)
    const label = event.event_type || 
                  event.task_id || 
                  event.operator_id || 
                  `Event ${index + 1}`;
    
    // Determine category and service
    const category = determineCategory(event);
    const service = determineService(event);
    const icon = getIcon(category, event.operator_type || '');
    
    // Build notes and details
    const notes = buildEventDetails(event, index);
    const extendedNotes = buildExtendedNotes(event);
    
    // Extract endpoint from event data if available
    const endpoint = event.event_data?.endpoint || 
                     event.event_data?.url || 
                     event.operator_params?.endpoint ||
                     undefined;
    
    // Create node - ALL events are 'task' type (no BPMN style)
    const node: FlowNode = {
      id: nodeId,
      type: 'task', // Always task type for Event Sourcing visualization
      position: { x: 0, y: 0 }, // Auto-layout will position these
      data: {
        label,
        type: 'task',
        notes, // Main details line
        extendedNotes, // Additional details
        // Status information
        status: eventStatus.status,
        statusColor: eventStatus.statusColor,
        statusIcon: eventStatus.statusIcon,
        // Event information
        task_id: event.task_id,
        operator_type: event.operator_type || 'Unknown',
        operator_id: event.operator_id,
        event_type: event.event_type,
        event_index: index,
        total_events: totalEvents,
        // Saga context
        state: saga.current_state,
        rpa_key_id: saga.rpa_key_id,
        saga_id: saga.saga_id,
        // Full event object for inspection
        event: event,
        // Metadata for styling
        rpa: {
          metadata: {
            icon,
            category,
            service,
            endpoint,
          },
        },
      },
      draggable: true,
      selectable: true,
      connectable: true,
    };
    
    nodes.push(node);
  });
  
  // Create edges based on event sequence (Event Sourcing: chronological flow)
  // Connect nodes in the order they appear in events
  for (let i = 0; i < nodes.length - 1; i++) {
    const sourceId = nodes[i].id;
    const targetId = nodes[i + 1].id;
    
    edges.push({
      id: `edge-${sourceId}-${targetId}`,
      source: sourceId,
      target: targetId,
      // Type will be determined by auto-layout
    });
  }
  
  // Apply auto-layout to position nodes and optimize edges
  const { nodes: layoutedNodes, edges: optimizedEdges } = applyAutoLayout(nodes, edges);
  
  return {
    nodes: layoutedNodes,
    edges: optimizedEdges,
  };
}

/**
 * Convert multiple SAGAs to FlowGraph format
 */
export function sagasToFlow(sagas: Saga[]): FlowGraph[] {
  return sagas.map(sagaToFlow);
}

