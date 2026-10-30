import { authHeaders } from "./private";
export type CardSummary = {
  id: string;
  slug: string;
  name_zh: string;
  name_en: string;
  arcana_type: "major" | "minor";
  suit: "wands" | "cups" | "swords" | "pentacles" | null;
  rank: string;
  upright_keywords: string[];
  reversed_keywords: string[];
  image_path: string | null;
};

export type Card = CardSummary & {
  upright_meaning: string;
  reversed_meaning: string;
  content_version: string;
  source_reference: {
    source_id: string;
    title: string;
    author: string;
    publication_year: number;
    url: string;
    reversed_url: string | null;
    locator: string;
    license: string;
    language: string;
    content_kind: string;
  };
};

export type CardPage = {
  items: CardSummary[];
  total: number;
  page: number;
  page_size: number;
};

export type Spread = {
  id: string;
  slug: string;
  name: string;
  description: string;
  version: string;
  positions: {
    index: number;
    name: string;
    description: string;
    x: number;
    y: number;
  }[];
};

export class ApiError extends Error {}

export async function fetchJson<T>(
  url: string,
  signal: AbortSignal,
): Promise<T> {
  const response = await fetch(url, { signal, headers: authHeaders() });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new ApiError(body?.error?.message ?? "加载失败，请稍后重试。");
  }
  return response.json();
}

export const suitNames = {
  wands: "权杖",
  cups: "圣杯",
  swords: "宝剑",
  pentacles: "星币",
};
