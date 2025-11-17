# RobotFlow

A Nuxt 3 application for designing and managing RPA workflow processes using Vueflow JSON format.

## Features

- **Flow Designer**: Visual workflow editor using Vue Flow
- **Vueflow JSON Format**: Native support for Vueflow-compatible JSON workflow format
- **Process Explorer**: Browse and manage workflow processes
- **Dark UI**: Beautiful dark theme with glassmorphism effects
- **TypeScript**: Full TypeScript support for type safety

## Getting Started

### Prerequisites

- Node.js 18+ and npm

### Installation

```bash
cd robotflow
npm install
```

### Development

```bash
npm run dev
```

The application will be available at `http://localhost:3001`

### Build

```bash
npm run build
npm run start
```

## Project Structure

```
robotflow/
├── src/
│   ├── components/
│   │   ├── FlowEditor.vue           # Main flow editor component
│   │   ├── FlowExplorer.vue         # File explorer sidebar
│   │   └── flow-nodes/              # Custom node components
│   ├── pages/
│   │   ├── index.vue                # Index page (redirects to home)
│   │   ├── home.vue                 # Home page with features
│   │   └── designer.vue             # Designer page with UI layout
│   ├── types/
│   │   └── flowTypes.ts             # Flow type definitions
│   ├── assets/
│   │   └── css/
│   │       └── main.css             # Global dark theme styles
│   ├── layouts/
│   │   └── default.vue              # Default layout with header and sidebar
│   └── middleware/                  # Route middleware (if any)
├── server/
│   └── api/
│       └── flow/
│           ├── list.get.ts           # API endpoint to list flow files
│           └── [name].get.ts        # API endpoint to get flow file
├── public/
│   └── processes/                   # Vueflow JSON process files
├── package.json
└── nuxt.config.ts
```

## Usage

1. **Open the Designer**: Navigate to `/designer` route or click "Open Designer" from home
2. **Browse Processes**: Use the file explorer sidebar to see available flow processes
3. **Load Process**: Click on a process file in the explorer to load it in the editor
4. **Edit Workflow**: Drag and connect nodes to create your workflow
5. **Export**: Click "Export" to download the current process as Vueflow JSON (`.vueflow.json`)

## Workflow Elements

### Start Node
- Represents the start of a workflow
- Visual: Green circular node with play icon

### End Node
- Represents the end of a workflow
- Visual: Red circular node with stop icon

### Task Node
- Represents a workflow task
- Visual: Rectangular node with task icon

### Gateway Node
- Represents a decision point in the workflow
- Visual: Diamond-shaped node

### Subprocess Node
- Represents a nested workflow process
- Visual: Purple rectangular node with border

## Vueflow JSON Format

Flow processes are stored in Vueflow-compatible JSON format (`.vueflow.json` files) for direct compatibility with Vue Flow library. The format supports:

- **Direct Vueflow compatibility**: No conversion needed
- **Type safety**: Full TypeScript type definitions
- **Version control friendly**: JSON diffs in Git
- **Rich metadata**: Support for RPA metadata, notes, and custom properties

### Example Vueflow JSON:

```json
{
  "nodes": [
    {
      "id": "StartEvent_1",
      "type": "start",
      "position": { "x": 100, "y": 300 },
      "data": {
        "label": "Start",
        "type": "start"
      }
    },
    {
      "id": "Task_1",
      "type": "task",
      "position": { "x": 450, "y": 300 },
      "data": {
        "label": "Process Data",
        "type": "task",
        "notes": "Process the input data"
      }
    }
  ],
  "edges": [
    {
      "id": "StartEvent_1->Task_1-0",
      "source": "StartEvent_1",
      "target": "Task_1",
      "type": "smoothstep"
    }
  ]
}
```

## Technical Details

- **Framework**: Nuxt 3
- **Flow Engine**: Vue Flow (@vue-flow/core)
- **Language**: TypeScript
- **Format**: JSON (Vueflow-compatible)
- **Styling**: Custom CSS with dark theme and glassmorphism effects

## File Locations

- **Flow Editor Component**: `src/components/FlowEditor.vue`
- **File Explorer**: `src/components/FlowExplorer.vue`
- **Designer Page**: `src/pages/designer.vue`
- **Flow Types**: `src/types/flowTypes.ts`
- **Node Components**: `src/components/flow-nodes/`
