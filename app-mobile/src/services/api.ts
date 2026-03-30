import { useAppStore } from "../store/appStore";
import type {
  AssistantResult,
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

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${getBaseUrl()}${path}`, {
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
  return requestJson<{ sessionId: string; createdAt: string }>("/api/assistant/session", {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export async function submitQuestion(question: string, sessionId?: string) {
  return requestJson<AssistantResult>("/api/assistant/query", {
    method: "POST",
    body: JSON.stringify({
      question,
      sessionId,
    }),
  });
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
