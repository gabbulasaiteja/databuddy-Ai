const getBaseUrl = () =>
  typeof window !== "undefined"
    ? ""
    : process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function getHeaders(): HeadersInit {
  const headers: HeadersInit = {
    "Content-Type": "application/json",
  };
  const apiKey =
    typeof window !== "undefined"
      ? (process.env.NEXT_PUBLIC_API_KEY as string | undefined)
      : (process.env.NEXT_PUBLIC_API_KEY as string | undefined);
  if (apiKey) {
    (headers as Record<string, string>)["X-API-Key"] = apiKey;
  }
  return headers;
}

async function fetchApi<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const base = getBaseUrl();
  const url = path.startsWith("http") ? path : `${base}${path}`;
  const res = await fetch(url, {
    ...options,
    headers: { ...getHeaders(), ...options.headers },
  });
  if (!res.ok) {
    const body = await res.text();
    let message = body;
    try {
      const j = JSON.parse(body);
      message = j.detail ?? j.message ?? body;
    } catch {
      // use body as message
    }
    throw new Error(message || `Request failed: ${res.status}`);
  }
  if (res.headers.get("content-type")?.includes("application/json")) {
    return res.json() as Promise<T>;
  }
  return res.blob() as unknown as Promise<T>;
}

export interface ImportResult {
  table_name: string;
  rows_imported: number;
}

export const api = {
  async importData(file: File, tableName: string): Promise<ImportResult> {
    const base = getBaseUrl();
    const form = new FormData();
    form.append("file", file);
    form.append("table_name", tableName);
    const headers: Record<string, string> = {};
    const apiKey =
      typeof window !== "undefined"
        ? (process.env.NEXT_PUBLIC_API_KEY as string | undefined)
        : (process.env.NEXT_PUBLIC_API_KEY as string | undefined);
    if (apiKey) {
      headers["X-API-Key"] = apiKey;
    }
    const res = await fetch(`${base}/api/import`, {
      method: "POST",
      body: form,
      headers,
    });
    if (!res.ok) {
      const body = await res.text();
      let message = body;
      try {
        const j = JSON.parse(body);
        message = j.detail ?? j.message ?? body;
      } catch {
        //
      }
      throw new Error(message || `Import failed: ${res.status}`);
    }
    return res.json() as Promise<ImportResult>;
  },

  async exportCSV(sql: string): Promise<Blob> {
    const base = getBaseUrl();
    const res = await fetch(`${base}/api/export/csv`, {
      method: "POST",
      headers: getHeaders(),
      body: JSON.stringify({ sql, use_transaction: false }),
    });
    if (!res.ok) {
      const body = await res.text();
      let message = body;
      try {
        const j = JSON.parse(body);
        message = j.detail ?? j.message ?? body;
      } catch {
        //
      }
      throw new Error(message || `Export failed: ${res.status}`);
    }
    return res.blob();
  },

  async exportJSON(sql: string): Promise<Blob> {
    const base = getBaseUrl();
    const res = await fetch(`${base}/api/export/json`, {
      method: "POST",
      headers: getHeaders(),
      body: JSON.stringify({ sql, use_transaction: false }),
    });
    if (!res.ok) {
      const body = await res.text();
      let message = body;
      try {
        const j = JSON.parse(body);
        message = j.detail ?? j.message ?? body;
      } catch {
        //
      }
      throw new Error(message || `Export failed: ${res.status}`);
    }
    return res.blob();
  },
};

export { fetchApi, getBaseUrl };
