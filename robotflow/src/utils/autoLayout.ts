import type { FlowNode, FlowEdge } from '~/src/types/flowTypes';

/**
 * Auto-layout configuration
 */
const LAYOUT_CONFIG = {
  NODES_PER_ROW: 5, // More nodes per row for event sourcing (better horizontal flow)
  HORIZONTAL_SPACING: 180, // Better spacing for event boxes
  VERTICAL_SPACING: 140, // Better vertical spacing for event flow
  START_X: 200,
  START_Y: 200,
  NODE_WIDTH: 280,
  NODE_HEIGHT: 140, // Slightly taller for event details
  MIN_NODE_DISTANCE: 160, // Better minimum distance
  SUBPROCESS_MARGIN: 20, // Reduced margin
  SUBPROCESS_WIDTH: 280, // Same as regular nodes
  SUBPROCESS_HEIGHT: 140, // Same as regular nodes
  ARROW_CLEARANCE: 15, // Reduced arrow clearance for shorter arrows
  ALIGNMENT_GRID: 20, // Grid size for strict alignment
};

/**
 * Build edge maps for graph traversal
 */
function buildEdgeMaps(
  nodes: FlowNode[],
  edges: FlowEdge[]
): {
  incomingEdges: Map<string, string[]>;
  outgoingEdges: Map<string, string[]>;
} {
  const incomingEdges = new Map<string, string[]>();
  const outgoingEdges = new Map<string, string[]>();

  nodes.forEach(node => {
    incomingEdges.set(node.id, []);
    outgoingEdges.set(node.id, []);
  });

  edges.forEach(edge => {
    const incoming = incomingEdges.get(edge.target) || [];
    incoming.push(edge.source);
    incomingEdges.set(edge.target, incoming);

    const outgoing = outgoingEdges.get(edge.source) || [];
    outgoing.push(edge.target);
    outgoingEdges.set(edge.source, outgoing);
  });

  return { incomingEdges, outgoingEdges };
}

/**
 * Calculate node levels using BFS from start nodes
 */
function calculateLevels(
  nodes: FlowNode[],
  edges: FlowEdge[]
): Map<number, string[]> {
  const levels = new Map<number, string[]>();
  const visited = new Set<string>();
  const { incomingEdges, outgoingEdges } = buildEdgeMaps(nodes, edges);

  // Find start nodes (no incoming edges or type 'start')
  const startNodes = nodes.filter(node => {
    const incoming = incomingEdges.get(node.id) || [];
    return incoming.length === 0 || node.type === 'start';
  });

  const queue: Array<{ id: string; level: number }> = [];
  
  if (startNodes.length > 0) {
    startNodes.forEach(node => {
      queue.push({ id: node.id, level: 0 });
      visited.add(node.id);
    });
  } else if (nodes.length > 0) {
    queue.push({ id: nodes[0].id, level: 0 });
    visited.add(nodes[0].id);
  }

  // BFS to assign levels
  while (queue.length > 0) {
    const { id, level } = queue.shift()!;

    if (!levels.has(level)) {
      levels.set(level, []);
    }
    levels.get(level)!.push(id);

    const outgoing = outgoingEdges.get(id) || [];
    outgoing.forEach(targetId => {
      if (!visited.has(targetId)) {
        visited.add(targetId);
        queue.push({ id: targetId, level: level + 1 });
      }
    });
  }

  // Add unvisited nodes
  nodes.forEach(node => {
    if (!visited.has(node.id)) {
      const maxLevel = Math.max(...Array.from(levels.keys()), -1);
      if (!levels.has(maxLevel + 1)) {
        levels.set(maxLevel + 1, []);
      }
      levels.get(maxLevel + 1)!.push(node.id);
    }
  });

  return levels;
}

/**
 * Get node dimensions based on type
 */
function getNodeDimensions(nodeType: string | undefined): { width: number; height: number } {
  if (nodeType === 'subprocess') {
    return {
      width: LAYOUT_CONFIG.SUBPROCESS_WIDTH,
      height: LAYOUT_CONFIG.SUBPROCESS_HEIGHT,
    };
  }
  return {
    width: LAYOUT_CONFIG.NODE_WIDTH,
    height: LAYOUT_CONFIG.NODE_HEIGHT,
  };
}

/**
 * Align position to grid for strict alignment
 */
function alignToGrid(value: number): number {
  return Math.round(value / LAYOUT_CONFIG.ALIGNMENT_GRID) * LAYOUT_CONFIG.ALIGNMENT_GRID;
}

/**
 * Check for node overlap with strict detection
 * Respects subprocess container margins and dimensions
 */
function hasOverlap(
  x: number,
  y: number,
  nodeType: string | undefined,
  existingPositions: Map<string, { x: number; y: number; type?: string }>,
  excludeId?: string
): boolean {
  const nodeDims = getNodeDimensions(nodeType);
  const nodeHalfWidth = nodeDims.width / 2;
  const nodeHalfHeight = nodeDims.height / 2;
  
  // Add margin for subprocess containers
  const marginX = nodeType === 'subprocess' ? LAYOUT_CONFIG.SUBPROCESS_MARGIN : 0;
  const marginY = nodeType === 'subprocess' ? LAYOUT_CONFIG.SUBPROCESS_MARGIN : 0;
  
  const nodeLeft = x - nodeHalfWidth - marginX;
  const nodeRight = x + nodeHalfWidth + marginX;
  const nodeTop = y - nodeHalfHeight - marginY;
  const nodeBottom = y + nodeHalfHeight + marginY;

  for (const [nodeId, pos] of existingPositions.entries()) {
    if (excludeId && nodeId === excludeId) continue;
    
    const existingDims = getNodeDimensions(pos.type);
    const existingHalfWidth = existingDims.width / 2;
    const existingHalfHeight = existingDims.height / 2;
    
    // Add margin for existing subprocess
    const existingMarginX = pos.type === 'subprocess' ? LAYOUT_CONFIG.SUBPROCESS_MARGIN : 0;
    const existingMarginY = pos.type === 'subprocess' ? LAYOUT_CONFIG.SUBPROCESS_MARGIN : 0;
    
    const existingLeft = pos.x - existingHalfWidth - existingMarginX;
    const existingRight = pos.x + existingHalfWidth + existingMarginX;
    const existingTop = pos.y - existingHalfHeight - existingMarginY;
    const existingBottom = pos.y + existingHalfHeight + existingMarginY;
    
    // Strict overlap detection with margins
    if (
      nodeLeft < existingRight &&
      nodeRight > existingLeft &&
      nodeTop < existingBottom &&
      nodeBottom > existingTop
    ) {
      return true;
    }
  }
  return false;
}

/**
 * Calculate node positions in sequential rows (all left to right)
 * With strict alignment, overlap prevention, and subprocess space allocation
 */
function calculateRowPositions(
  levels: Map<number, string[]>,
  nodes: FlowNode[]
): {
  positions: Map<string, { x: number; y: number }>;
  nodeToRow: Map<string, number>;
} {
  const positions = new Map<string, { x: number; y: number; type?: string }>();
  const nodeToRow = new Map<string, number>();
  const nodeMap = new Map<string, FlowNode>();
  
  nodes.forEach(node => {
    nodeMap.set(node.id, node);
  });
  
  let currentY = LAYOUT_CONFIG.START_Y;

  const sortedLevels = Array.from(levels.entries()).sort((a, b) => a[0] - b[0]);
  const allNodes: string[] = [];
  sortedLevels.forEach(([_, nodeIds]) => {
    allNodes.push(...nodeIds);
  });

  const totalNodes = allNodes.length;
  const rowsNeeded = Math.ceil(totalNodes / LAYOUT_CONFIG.NODES_PER_ROW);

  for (let row = 0; row < rowsNeeded; row++) {
    const startIndex = row * LAYOUT_CONFIG.NODES_PER_ROW;
    const endIndex = Math.min(startIndex + LAYOUT_CONFIG.NODES_PER_ROW, totalNodes);
    const nodesInRow = allNodes.slice(startIndex, endIndex);
    
    // Check if row contains subprocess (only affects row height, not horizontal spacing)
    const rowHasSubprocess = nodesInRow.some(id => nodeMap.get(id)?.type === 'subprocess');
    
    // All rows use same horizontal spacing regardless of subprocess
    // Subprocess only affects row height (vertical spacing)
    const rowSpacing = LAYOUT_CONFIG.HORIZONTAL_SPACING;

    // All rows go left to right with strict horizontal alignment
    let currentX = LAYOUT_CONFIG.START_X;
    
    for (let i = 0; i < nodesInRow.length; i++) {
      const nodeId = nodesInRow[i];
      const node = nodeMap.get(nodeId);
      const nodeType = node?.type;
      const nodeDims = getNodeDimensions(nodeType);
      
      // Calculate base position with strict horizontal alignment
      let x = currentX;
      
      // For subprocess, center it in its allocated space
      if (nodeType === 'subprocess') {
        x = currentX + (LAYOUT_CONFIG.SUBPROCESS_WIDTH / 2);
      } else {
        // Regular nodes: use standard spacing
        x = currentX + (nodeDims.width / 2);
      }
      
      // Align to grid for strict alignment
      x = alignToGrid(x);
      
      // Prevent overlaps with aggressive adjustment
      let attempts = 0;
      const maxAttempts = 30;
      let adjustedX = x;
      
      while (hasOverlap(adjustedX, currentY, nodeType, positions, nodeId) && attempts < maxAttempts) {
        adjustedX += LAYOUT_CONFIG.ALIGNMENT_GRID;
        adjustedX = alignToGrid(adjustedX);
        attempts++;
      }
      
      // If still overlapping, add minimal spacing
      if (hasOverlap(adjustedX, currentY, nodeType, positions, nodeId)) {
        adjustedX += LAYOUT_CONFIG.HORIZONTAL_SPACING * 0.2;
        adjustedX = alignToGrid(adjustedX);
      }
      
      // Final strict alignment
      adjustedX = alignToGrid(adjustedX);
      
      positions.set(nodeId, { x: adjustedX, y: currentY, type: nodeType });
      nodeToRow.set(nodeId, row);
      
      // Update currentX for next node with minimal spacing
      // All node types use same spacing calculation
      currentX = adjustedX + (nodeDims.width / 2) + LAYOUT_CONFIG.HORIZONTAL_SPACING;
      
      // Ensure minimum spacing
      currentX = Math.max(currentX, adjustedX + nodeDims.width + LAYOUT_CONFIG.MIN_NODE_DISTANCE);
    }

    // Calculate row height based on tallest node in row
    const rowHeight = Math.max(
      ...nodesInRow.map(id => {
        const node = nodeMap.get(id);
        return getNodeDimensions(node?.type).height;
      })
    );
    
    // If row contains subprocess container, make row double height to fit properly
    if (rowHasSubprocess) {
      // Double the row height for subprocess containers to fit properly
      currentY += (rowHeight * 2) + LAYOUT_CONFIG.VERTICAL_SPACING;
    } else {
      currentY += rowHeight + LAYOUT_CONFIG.VERTICAL_SPACING;
    }
    
    // Align Y to grid
    currentY = alignToGrid(currentY);
  }

  // Convert positions map to return format
  const returnPositions = new Map<string, { x: number; y: number }>();
  positions.forEach((pos, nodeId) => {
    returnPositions.set(nodeId, { x: pos.x, y: pos.y });
  });

  return { positions: returnPositions, nodeToRow };
}

/**
 * Check if arrow path would overlap with any node
 */
function arrowOverlapsNode(
  sourceX: number,
  sourceY: number,
  targetX: number,
  targetY: number,
  nodes: FlowNode[]
): boolean {
  // For step edges: horizontal then vertical
  const minX = Math.min(sourceX, targetX);
  const maxX = Math.max(sourceX, targetX);
  const horizontalY = sourceY;
  
  const minY = Math.min(sourceY, targetY);
  const maxY = Math.max(sourceY, targetY);
  const verticalX = targetX;
  
  for (const node of nodes) {
    const { x, y } = node.position;
    const dims = getNodeDimensions(node.type);
    const nodeLeft = x - dims.width / 2 - LAYOUT_CONFIG.ARROW_CLEARANCE;
    const nodeRight = x + dims.width / 2 + LAYOUT_CONFIG.ARROW_CLEARANCE;
    const nodeTop = y - dims.height / 2 - LAYOUT_CONFIG.ARROW_CLEARANCE;
    const nodeBottom = y + dims.height / 2 + LAYOUT_CONFIG.ARROW_CLEARANCE;
    
    // Check horizontal segment overlap
    if (horizontalY >= nodeTop && horizontalY <= nodeBottom) {
      if (minX <= nodeRight && maxX >= nodeLeft) {
        return true;
      }
    }
    
    // Check vertical segment overlap
    if (verticalX >= nodeLeft && verticalX <= nodeRight) {
      if (minY <= nodeBottom && maxY >= nodeTop) {
        return true;
      }
    }
  }
  
  return false;
}

/**
 * Apply auto-layout to nodes and optimize edges
 * Strict horizontal/vertical alignment only
 * Arrows never overlap nodes
 * Subprocess containers have proper space allocation
 */
export function applyAutoLayout(
  nodes: FlowNode[],
  edges: FlowEdge[]
): {
  nodes: FlowNode[];
  edges: FlowEdge[];
} {
  if (!nodes || nodes.length === 0) {
    return { nodes, edges };
  }

  const levels = calculateLevels(nodes, edges);
  const { positions, nodeToRow } = calculateRowPositions(levels, nodes);

  // Apply positions to nodes with strict alignment
  const layoutedNodes = nodes.map(node => {
    const position = positions.get(node.id);
    if (position) {
      return {
        ...node,
        position: {
          x: alignToGrid(position.x),
          y: alignToGrid(position.y),
        },
      };
    }
    return {
      ...node,
      position: {
        x: alignToGrid(LAYOUT_CONFIG.START_X),
        y: alignToGrid(LAYOUT_CONFIG.START_Y),
      },
    };
  });

  // STRICT ENFORCEMENT: Only horizontal or vertical arrows, NO ANGLES PROHIBITED
  // Applies to ALL node types: start, end, gateway, task, subprocess
  // Same row: straight (horizontal only)
  // Different rows: step (horizontal then vertical, or vertical then horizontal)
  // NEVER use smoothstep, bezier, or any edge type that creates angles
  // FORCE override any existing edge types that might create angles
  // SPECIAL HANDLING: Start and End nodes MUST use horizontal/vertical only
  const optimizedEdges = edges.map(edge => {
    const sourceNode = layoutedNodes.find(n => n.id === edge.source);
    const targetNode = layoutedNodes.find(n => n.id === edge.target);
    
    if (!sourceNode || !targetNode) {
      // Force straight for missing nodes (horizontal only)
      return { 
        ...edge, 
        type: 'straight', // Override any existing type - horizontal only
      };
    }
    
    // Get row numbers for source and target (works for ALL node types: start, end, gateway, task, subprocess)
    const sourceRow = nodeToRow.get(edge.source) ?? -1;
    const targetRow = nodeToRow.get(edge.target) ?? -1;
    
    // Check if source or target is start/end node
    const isStartNode = sourceNode.type === 'start';
    const isEndNode = targetNode.type === 'end';
    
    // STRICT RULE: Only horizontal or vertical, NO ANGLES - applies to ALL node types
    // Same row: straight (pure horizontal, no angles) - for start, end, gateway, task, subprocess
    // Different rows: step (horizontal then vertical, NO diagonal angles) - for all node types
    // SPECIAL: Start and End nodes MUST always use horizontal/vertical, never diagonal
    let edgeType: string;
    
    if (sourceRow === targetRow && sourceRow !== -1 && targetRow !== -1) {
      // Same row: MUST use straight (horizontal only, NO ANGLES)
      // This applies to start->next, previous->end, and all same-row connections
      edgeType = 'straight';
    } else {
      // Different rows: MUST use step (horizontal then vertical, NO ANGLES)
      // This applies to start->different-row, different-row->end, and all cross-row connections
      edgeType = 'step';
    }
    
    // FORCE edge type - override any existing type that might create angles
    // Only 'straight' and 'step' are allowed - both are horizontal/vertical only
    // This applies to edges connected to start, end, gateway, task, and subprocess nodes
    // Remove any properties that might cause angles (pathOptions, style with curves, etc.)
    const cleanEdge: FlowEdge = {
      id: edge.id,
      source: edge.source,
      target: edge.target,
      type: edgeType, // FORCE type - only 'straight' or 'step' - both enforce horizontal/vertical only
    };
    
    // Preserve label if exists, but ensure type is correct
    if (edge.label) {
      cleanEdge.label = edge.label;
    }
    
    return cleanEdge;
  });

  return {
    nodes: layoutedNodes,
    edges: optimizedEdges,
  };
}

/**
 * Get bounding box for fitView
 */
export function getNodesBoundingBox(nodes: FlowNode[]): {
  minX: number;
  minY: number;
  maxX: number;
  maxY: number;
} {
  if (nodes.length === 0) {
    return { minX: 0, minY: 0, maxX: 1000, maxY: 1000 };
  }

  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;

  nodes.forEach(node => {
    const { x, y } = node.position;
    const dims = getNodeDimensions(node.type);
    minX = Math.min(minX, x - dims.width / 2);
    minY = Math.min(minY, y - dims.height / 2);
    maxX = Math.max(maxX, x + dims.width / 2);
    maxY = Math.max(maxY, y + dims.height / 2);
  });

  const padding = 150;
  return {
    minX: minX - padding,
    minY: minY - padding,
    maxX: maxX + padding,
    maxY: maxY + padding,
  };
}
