import { readFile, stat } from 'fs/promises';
import { join } from 'path';

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
 * API endpoint to get a specific Vueflow JSON process file by name
 * GET /api/flow/[name]
 */
export default defineEventHandler(async (event) => {
  try {
    const name = getRouterParam(event, 'name');
    if (!name) {
      throw createError({
        statusCode: 400,
        statusMessage: 'File name is required'
      });
    }

    // Security: prevent path traversal
    if (name.includes('..') || name.includes('/') || name.includes('\\')) {
      throw createError({
        statusCode: 400,
        statusMessage: 'Invalid file name'
      });
    }

    const processesPath = getProcessesPath();
    const filePath = join(processesPath, name);

    console.log('[FlowService] Reading file:', filePath);

    // Check if file exists
    try {
      const fileStats = await stat(filePath);
      if (!fileStats.isFile()) {
        throw createError({
          statusCode: 404,
          statusMessage: `File not found: ${name}`
        });
      }
    } catch (statError: any) {
      if (statError.statusCode) {
        throw statError;
      }
      console.error('[FlowService] File stat error:', statError);
      throw createError({
        statusCode: 404,
        statusMessage: `File not found: ${name}`
      });
    }

    // Read file as JSON
    const content = await readFile(filePath, 'utf-8');
    let jsonData;
    
    try {
      jsonData = JSON.parse(content);
    } catch (parseError) {
      throw createError({
        statusCode: 400,
        statusMessage: 'Invalid JSON format'
      });
    }

    // Set proper headers
    setHeader(event, 'Content-Type', 'application/json; charset=utf-8');
    setHeader(event, 'Cache-Control', 'no-cache, no-store, must-revalidate');

    return jsonData;
  } catch (error: any) {
    console.error('[FlowService] Error reading file:', error);
    if (error && typeof error === 'object' && 'statusCode' in error) {
      throw error;
    }
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    throw createError({
      statusCode: 500,
      statusMessage: `Failed to read file: ${errorMessage}`
    });
  }
});
