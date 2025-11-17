import { readdir, stat } from 'fs/promises';
import { join } from 'path';

export interface FlowFile {
  name: string;
  path: string;
}

/**
 * Get the path to the public/processes directory
 * Always uses source public folder, not build output
 */
function getProcessesPath(): string {
  // Always use source public folder relative to project root
  const paths = [
    // Strategy 1: If running from robotflow directory
    join(process.cwd(), 'public', 'processes'),
    // Strategy 2: If running from workspace root
    join(process.cwd(), 'robotflow', 'public', 'processes'),
  ];

  // Return first path (will be validated before use)
  return paths[0];
}

/**
 * Check if a file is a Vueflow JSON file
 */
function isFlowFile(filename: string): boolean {
  return filename.endsWith('.vueflow.json');
}

/**
 * API endpoint to list all Vueflow JSON process files
 * GET /api/flow/list
 */
export default defineEventHandler(async (): Promise<FlowFile[]> => {
  try {
    const processesPath = getProcessesPath();
    
    // Validate directory exists
    try {
      const stats = await stat(processesPath);
      if (!stats.isDirectory()) {
        console.error(`[FlowService] Path is not a directory: ${processesPath}`);
        return [];
      }
    } catch (error) {
      console.error(`[FlowService] Directory does not exist: ${processesPath}`, error);
      return [];
    }
    
    console.log(`[FlowService] Reading directory: ${processesPath}`);
    const files = await readdir(processesPath, { withFileTypes: true });
    console.log(`[FlowService] Found ${files.length} items in directory`);
    
    const flowFiles = files
      .filter(file => {
        const isFile = file.isFile();
        const isFlow = isFlowFile(file.name);
        if (isFile) {
          console.log(`[FlowService] File: ${file.name}, isFlow: ${isFlow}`);
        }
        return isFile && isFlow;
      })
      .map(file => ({
        name: file.name,
        path: `/processes/${file.name}`
      }))
      .sort((a, b) => a.name.localeCompare(b.name));

    console.log(`[FlowService] Returning ${flowFiles.length} flow files:`, flowFiles.map(f => f.name));
    return flowFiles;
  } catch (error) {
    console.error('[FlowService] Error listing files:', error);
    return [];
  }
});
