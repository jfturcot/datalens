import type {
  ConversationDetailResponse,
  ConversationResponse,
  SessionResponse,
  UploadResponse,
} from "./types";

const BASE = "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    credentials: "include",
    ...init,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export async function createSession(password?: string): Promise<SessionResponse> {
  return request<SessionResponse>("/sessions", {
    method: "POST",
    headers: password ? { "Content-Type": "application/json" } : undefined,
    body: password ? JSON.stringify({ password }) : undefined,
  });
}

export async function getMySession(): Promise<SessionResponse> {
  return request<SessionResponse>("/sessions/me");
}

export async function uploadFile(file: File): Promise<UploadResponse> {
  const form = new FormData();
  form.append("file", file);
  return request<UploadResponse>("/upload", {
    method: "POST",
    body: form,
  });
}

export async function listConversations(): Promise<ConversationResponse[]> {
  return request<ConversationResponse[]>("/conversations");
}

export async function getConversation(
  id: string,
): Promise<ConversationDetailResponse> {
  return request<ConversationDetailResponse>(`/conversations/${id}`);
}

export async function deleteConversation(id: string): Promise<void> {
  await fetch(`${BASE}/conversations/${id}`, {
    method: "DELETE",
    credentials: "include",
  });
}
