/**
 * API endpoint to list all SAGAs from rpa-api
 * GET /api/saga/list
 */

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
 * Get RPA API base URL from environment variable
 */
function getRpaApiBaseUrl(): string {
  const apiUrl = process.env.RPA_API_BASE_URL || 'http://localhost:3000';
  return apiUrl.endsWith('/') ? apiUrl.slice(0, -1) : apiUrl;
}

/**
 * API endpoint to list all SAGAs from rpa-api
 */
export default defineEventHandler(async (event): Promise<Saga[]> => {
  try {
    const query = getQuery(event);
    const limit = query.limit ? parseInt(String(query.limit), 10) : 100;
    const offset = query.offset ? parseInt(String(query.offset), 10) : 0;

    const baseUrl = getRpaApiBaseUrl();
    const url = `${baseUrl}/api/v1/saga/list?limit=${limit}&offset=${offset}`;

    console.log(`[SagaService] Fetching SAGAs from: ${url}`);

    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorText = await response.text().catch(() => 'Unknown error');
      throw new Error(`HTTP ${response.status}: ${errorText}`);
    }

    const sagas = await response.json();

    if (!Array.isArray(sagas)) {
      throw new Error('Invalid response format: expected array');
    }

    console.log(`[SagaService] Fetched ${sagas.length} SAGAs`);
    return sagas;
  } catch (error: any) {
    console.error('[SagaService] Error fetching SAGAs:', error);
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    throw createError({
      statusCode: 500,
      statusMessage: `Failed to fetch SAGAs: ${errorMessage}`,
    });
  }
});

