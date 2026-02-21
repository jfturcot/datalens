export interface SessionResponse {
  id: string;
  created_at: string;
}

export interface ColumnInfo {
  name: string;
  type: string;
}

export interface UploadResponse {
  conversation_id: string;
  filename: string;
  table_name: string;
  row_count: number;
  columns: ColumnInfo[];
}

export interface ConversationResponse {
  id: string;
  filename: string;
  table_name: string;
  row_count: number | null;
  created_at: string;
}

export interface ConversationMessage {
  role: string;
  content: string;
  sql?: string;
  display?: DisplayData;
}

export interface ConversationDetailResponse {
  id: string;
  filename: string;
  table_name: string;
  row_count: number | null;
  created_at: string;
  messages: ConversationMessage[];
}

export interface DisplayData {
  type: "text" | "table" | "bar_chart" | "line_chart" | "pie_chart" | "scatter_plot";
  title?: string;
  data: Record<string, unknown>[];
  x_axis?: string;
  y_axis?: string;
  label_key?: string;
  value_key?: string;
}

export interface MessageCompleteData {
  content: string;
  sql?: string;
  display?: DisplayData;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sql?: string;
  display?: DisplayData;
  isStreaming?: boolean;
  hidden?: boolean;
}

export interface ToolStatus {
  tool: string;
  active: boolean;
}
