import { ApiError } from "./catalog";

const TOKEN_KEY = "ai-tarot-session";
export function authHeaders(): Record<string, string> {
  const token = sessionStorage.getItem(TOKEN_KEY);
  return token ? { Authorization: "Bearer " + token } : {};
}
export function saveToken(token: string) {
  sessionStorage.setItem(TOKEN_KEY, token);
}
export function clearToken() {
  sessionStorage.removeItem(TOKEN_KEY);
}
export async function request<T>(
  url: string,
  body?: unknown,
  key?: string,
): Promise<T> {
  const response = await fetch("/api/v1" + url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...(key ? { "Idempotency-Key": key } : {}),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => null);
    throw new ApiError(data?.error?.message ?? "请求失败，请稍后重试。");
  }
  return response.status === 204 ? (undefined as T) : response.json();
}

export type Reading = {
  id: string;
  question: string;
  category: string;
  background: string | null;
  status: "pending_interpretation" | "processing" | "completed" | "failed";
  spread: { name: string };
  cards: {
    card_id: string;
    name: string;
    position_index: number;
    position_name: string;
    orientation: "upright" | "reversed";
    card_snapshot: {
      content_version: string;
      upright_meaning: string;
      reversed_meaning: string;
      source_reference: {
        url: string;
        reversed_url?: string | null;
        title: string;
      };
    };
  }[];
  interpretation: Interpretation | null;
};

export type Interpretation = {
  summary: string;
  scope_note: string;
  card_interpretations: {
    card_id: string;
    position_index: number;
    position_name: string;
    orientation: "upright" | "reversed";
    traditional_meaning: string;
    contextual_interpretation: string;
    source_ids: string[];
  }[];
  synthesis: string;
  possible_scenarios: { description: string; basis: string }[];
  action_suggestions: string[];
  reflection_questions: string[];
  uncertainties: string[];
};
