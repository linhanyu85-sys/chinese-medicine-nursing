import { useAppStore } from "../store/appStore";
import type {
  AssistantResult,
  AssistantSessionDetail,
  AssistantSessionSummary,
  ArticleCard,
  ArticleDetail,
  HealthStatus,
  HomePayload,
  ManagementOverview,
  TreeNode,
} from "../types";

function getBaseUrl() {
  return useAppStore.getState().backendUrl.replace(/\/+$/, "");
}

const REQUEST_TIMEOUT_MS = 12000;
const RETRY_TIMES = 0;

async function fetchWithTimeout(url: string, timeoutMs: number, init?: RequestInit) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, {
      ...init,
      signal: controller.signal,
    });
  } finally {
    clearTimeout(timeout);
  }
}

async function requestJson<T>(path: string, init?: RequestInit, timeoutMs: number = REQUEST_TIMEOUT_MS): Promise<T> {
  const url = `${getBaseUrl()}${path}`;
  let lastError: Error | null = null;

  for (let attempt = 0; attempt <= RETRY_TIMES; attempt += 1) {
    try {
      const response = await fetchWithTimeout(url, timeoutMs, {
        ...init,
        headers: {
          "Content-Type": "application/json; charset=utf-8",
          ...(init?.headers || {}),
        },
      });

      const text = await response.text();
      const payload = text ? JSON.parse(text) : {};
      if (!response.ok) {
        const message = payload?.error || "请求失败";
        throw new Error(message);
      }
      return payload as T;
    } catch (err) {
      const abortError =
        typeof err === "object" &&
        err !== null &&
        "name" in err &&
        (err as { name?: string }).name === "AbortError";
      const message =
        abortError
          ? "请求超时，请稍后重试"
          : err instanceof Error
            ? err.message
            : "网络异常，请稍后重试";

      lastError = new Error(message);
      if (attempt < RETRY_TIMES) {
        continue;
      }
    }
  }

  throw lastError || new Error("请求失败");
}

export async function fetchHealthStatus() {
  return requestJson<HealthStatus>("/api/health");
}

export async function fetchHomePayload() {
  return requestJson<HomePayload>("/api/home");
}

export async function fetchTree() {
  const payload = await requestJson<{ tree: TreeNode[] }>("/api/knowledge/tree");
  return payload.tree;
}

export async function fetchArticleList(query = "", tag = "") {
  const search = new URLSearchParams();
  if (query) {
    search.set("query", query);
  }
  if (tag) {
    search.set("tag", tag);
  }
  search.set("limit", "60");
  const payload = await requestJson<{ items: ArticleCard[] }>(`/api/knowledge/articles?${search.toString()}`);
  return payload.items;
}

export async function fetchArticleDetail(articleId: string) {
  return requestJson<ArticleDetail>(`/api/knowledge/article/${encodeURIComponent(articleId)}`);
}

export async function createSession() {
  return requestJson<{ sessionId: string; createdAt: string; title: string }>("/api/assistant/session", {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export async function createNamedSession(title?: string) {
  return requestJson<{ sessionId: string; createdAt: string }>("/api/assistant/session", {
    method: "POST",
    body: JSON.stringify({
      title,
    }),
  });
}

export async function submitQuestion(question: string, sessionId?: string) {
  return requestJson<AssistantResult>("/api/assistant/query", {
    method: "POST",
    body: JSON.stringify({
      question,
      sessionId,
    }),
  }, 90000);
}

export async function fetchAssistantSessions(limit = 30) {
  const payload = await requestJson<{ items: AssistantSessionSummary[] }>(`/api/assistant/sessions?limit=${limit}`);
  return payload.items;
}

export async function fetchAssistantSessionDetail(sessionId: string) {
  return requestJson<AssistantSessionDetail>(`/api/assistant/session/${encodeURIComponent(sessionId)}`);
}

export async function fetchManagementOverview() {
  return requestJson<ManagementOverview>("/api/management/overview");
}

export async function reloadKnowledgeBase() {
  return requestJson<{ result: string; articleCount: number }>("/api/management/reload", {
    method: "POST",
    body: JSON.stringify({}),
  });
}
