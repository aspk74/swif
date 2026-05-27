/* ── Types ──────────────────────────────────────────────────── */

export interface ScoreData {
  score: number;
  total_rules: number;
  active_violations: number;
}

export interface DeviceCountData {
  count: number;
}

export interface Rule {
  _id?: string;
  suggested_id: string;
  category: string;
  severity: string;
  technical_parameter: string;
  expected_value: string;
  logic: string;
  source_document?: string;
  chunk_reference?: string;
  remediation_command?: string;
}

export interface Violation {
  _id: string;
  device_id: string;
  device_name?: string;
  os_type?: string;
  technical_parameter: string;
  expected_value?: string;
  actual_value?: string;
  severity: string;
  action_taken: string;
  violated_at: string;
  grace_period_expires_at?: string;
  remediation_logs?: string;
  remediation_command?: string;
}

export interface SimulateDriftResult {
  status: string;
  device_id: string;
  parameter: string;
}

export interface RemediationResult {
  status: string;
  logs?: string;
  detail?: string;
}

export interface ApiError {
  status: "error";
  detail: string;
}

/* ── Fetch Helpers ─────────────────────────────────────────── */

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, options);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

/* ── API Functions ─────────────────────────────────────────── */

export async function fetchScore(): Promise<ScoreData> {
  return fetchJson<ScoreData>("/api/score");
}

export async function fetchDeviceCount(): Promise<DeviceCountData> {
  return fetchJson<DeviceCountData>("/api/devices/count");
}

export async function fetchRules(
  limit = 200,
  skip = 0
): Promise<Rule[]> {
  return fetchJson<Rule[]>(`/api/rules?limit=${limit}&skip=${skip}`);
}

export async function fetchViolations(
  limit = 100,
  skip = 0,
  status = "all"
): Promise<Violation[]> {
  return fetchJson<Violation[]>(
    `/api/violations?limit=${limit}&skip=${skip}&status=${status}`
  );
}

export async function executeRemediation(
  violationId: string
): Promise<RemediationResult> {
  return fetchJson<RemediationResult>(`/api/remediate/${violationId}`, {
    method: "POST",
  });
}

export async function simulateDrift(): Promise<SimulateDriftResult> {
  return fetchJson<SimulateDriftResult>("/api/simulate-drift", {
    method: "POST",
  });
}

export async function fetchMetrics(): Promise<Record<string, number>> {
  const res = await fetch("/metrics");
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const text = await res.text();
  const metrics: Record<string, number> = {};
  for (const line of text.split("\n")) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const parts = trimmed.split(" ");
    if (parts.length >= 2) {
      const val = parseFloat(parts[1]);
      if (!isNaN(val)) metrics[parts[0]] = val;
    }
  }
  return metrics;
}

export async function uploadPolicyPdf(
  file: File,
  onProgress: (message: string) => void
): Promise<{ extracted: number; inserted: number; updated: number }> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch("/api/rules/upload-pdf", {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`Upload failed: ${errorText}`);
  }

  if (!res.body) {
    throw new Error("No response body returned");
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");

    // Process all complete lines
    for (let i = 0; i < lines.length - 1; i++) {
      const line = lines[i].trim();
      if (!line) continue;

      let data: any = null;
      try {
        data = JSON.parse(line);
      } catch (err) {
        console.error("Failed to parse stream line:", line, err);
        continue;
      }

      if (data.type === "progress") {
        onProgress(data.message);
      } else if (data.type === "error") {
        throw new Error(data.message);
      } else if (data.type === "done") {
        return {
          extracted: data.rules_extracted,
          inserted: data.inserted,
          updated: data.updated,
        };
      }
    }
    // Keep the last incomplete line in buffer
    buffer = lines[lines.length - 1];
  }

  throw new Error("Stream closed unexpectedly before completion.");
}
