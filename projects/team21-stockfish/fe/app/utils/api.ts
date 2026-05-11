import axios from "axios";
import type {
  SectorCode,
  ChatRequest,
  ChatResponse,
  SectorAnalysisResponse,
} from "~/types/api";

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

export const SECTOR_CODE_MAP: Record<string, SectorCode | undefined> = {
  반도체: "semiconductor",
  제약: "pharmaceutical",
};

export async function fetchSectorAnalysis(
  sector: SectorCode,
  refresh = true,
): Promise<SectorAnalysisResponse> {
  const { data } = await apiClient.get<SectorAnalysisResponse>(
    `/api/v1/sectors/${sector}/analysis`,
    { params: { refresh } },
  );
  return data;
}

export async function postChat(
  body: ChatRequest,
  refresh = true,
): Promise<ChatResponse> {
  const { data } = await apiClient.post<ChatResponse>("/api/v1/chat", body, {
    params: { refresh },
  });
  return data;
}
