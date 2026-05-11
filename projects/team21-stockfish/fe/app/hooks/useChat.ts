import { useState, useEffect, useCallback } from "react";
import { useMutation } from "@tanstack/react-query";
import { postChat, fetchSectorAnalysis, SECTOR_CODE_MAP } from "~/utils/api";
import type { ChatTurn, SectorAnalysisResponse, WarningMessage, SectorCode } from "~/types/api";

export type UserMessage = {
  id: string;
  role: "user";
  type: "text";
  content: string;
};

export type AssistantTextMessage = {
  id: string;
  role: "assistant";
  type: "text";
  content: string;
  request_type?: "sector_analysis" | "term_explanation" | "out_of_scope";
  safetyNotice?: string | null;
  warnings?: WarningMessage[];
};

export type SectorAnalysisMessage = {
  id: string;
  role: "assistant";
  type: "sector_analysis_card";
  data: SectorAnalysisResponse;
};

export type LoadingMessage = {
  id: string;
  role: "assistant";
  type: "loading";
};

export type TermExplanationMessage = {
  id: string;
  role: "assistant";
  type: "term_explanation_card";
  term: string;
  definition: string;
  safetyNotice?: string | null;
  warnings?: WarningMessage[];
};

export type ErrorMessage = {
  id: string;
  role: "assistant";
  type: "error";
  content: string;
};

export type ChatMessage =
  | UserMessage
  | AssistantTextMessage
  | SectorAnalysisMessage
  | TermExplanationMessage
  | LoadingMessage
  | ErrorMessage;

const LOADING_MSG_ID = "__loading__";

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(() =>
    typeof window !== "undefined" ? sessionStorage.getItem("chat_session_id") : null,
  );
  const [history, setHistory] = useState<ChatTurn[]>([]);

  useEffect(() => {
    if (sessionId) sessionStorage.setItem("chat_session_id", sessionId);
  }, [sessionId]); // useEffect는 브라우저에서만 실행되므로 guard 불필요

  const { mutate: sendMessage, isPending } = useMutation({
    mutationFn: ({ content, sectorCode }: { content: string; sectorCode?: SectorCode | null }) =>
      postChat({
        message: content,
        sector: sectorCode ?? null,
        session_id: sessionId,
        history,
      }),

    onMutate: ({ content }) => {
      const userMsg: UserMessage = {
        id: crypto.randomUUID(),
        role: "user",
        type: "text",
        content,
      };
      const loadingMsg: LoadingMessage = {
        id: LOADING_MSG_ID,
        role: "assistant",
        type: "loading",
      };
      setMessages((prev) => [...prev, userMsg, loadingMsg]);
      return { userMsg };
    },

    onSuccess: (data, variables) => {
      let assistantMsg: AssistantTextMessage | SectorAnalysisMessage | TermExplanationMessage;

      if (data.request_type === "term_explanation") {
        assistantMsg = {
          id: crypto.randomUUID(),
          role: "assistant",
          type: "term_explanation_card",
          term: variables.content,
          definition: data.answer,
          safetyNotice: data.safety_notice,
          warnings: data.warnings,
        } satisfies TermExplanationMessage;
      } else if (data.request_type === "sector_analysis") {
        assistantMsg = {
          id: crypto.randomUUID(),
          role: "assistant",
          type: "sector_analysis_card",
          data: {
            sector: variables.sectorCode ?? null,
            beginner_summary: data.answer,
            key_evidence: [],
            confidence: 0.5,
            caution: data.safety_notice ?? "",
            warnings: data.warnings,
          },
        } satisfies SectorAnalysisMessage;
      } else {
        assistantMsg = {
          id: crypto.randomUUID(),
          role: "assistant",
          type: "text",
          content: data.answer,
          request_type: data.request_type,
          safetyNotice: data.safety_notice,
          warnings: data.warnings,
        } satisfies AssistantTextMessage;
      }

      setMessages((prev) => prev.filter((m) => m.id !== LOADING_MSG_ID).concat(assistantMsg));
      if (data.session_id) setSessionId(data.session_id);
      setHistory((prev) => [
        ...prev,
        { role: "user", content: variables.content },
        { role: "assistant", content: data.answer },
      ]);
    },

    onError: (_error, _variables, context) => {
      setMessages((prev) =>
        prev
          .filter((m) => m.id !== LOADING_MSG_ID)
          .concat({
            id: crypto.randomUUID(),
            role: "assistant",
            type: "error",
            content: "메시지 전송에 실패했습니다. 다시 시도해 주세요.",
          }),
      );
      if (context?.userMsg) {
        setMessages((prev) => prev.filter((m) => m.id !== context.userMsg.id));
      }
    },
  });

  const sendSectorAnalysis = useCallback(
    async (sectorLabel: string) => {
      const sectorCode = SECTOR_CODE_MAP[sectorLabel];
      const messageContent = `${sectorLabel} 섹터 분석해줘`;

      if (sectorCode) {
        const userMsg: UserMessage = {
          id: crypto.randomUUID(),
          role: "user",
          type: "text",
          content: messageContent,
        };
        const loadingMsg: LoadingMessage = {
          id: LOADING_MSG_ID,
          role: "assistant",
          type: "loading",
        };
        setMessages((prev) => [...prev, userMsg, loadingMsg]);

        try {
          const data = await fetchSectorAnalysis(sectorCode);
          setMessages((prev) =>
            prev
              .filter((m) => m.id !== LOADING_MSG_ID)
              .concat({
                id: crypto.randomUUID(),
                role: "assistant",
                type: "sector_analysis_card",
                data,
              }),
          );
          setHistory((prev) => [
            ...prev,
            { role: "user", content: messageContent },
            { role: "assistant", content: data.beginner_summary },
          ]);
        } catch {
          setMessages((prev) =>
            prev
              .filter((m) => m.id !== userMsg.id && m.id !== LOADING_MSG_ID)
              .concat({
                id: crypto.randomUUID(),
                role: "assistant",
                type: "error",
                content: "섹터 분석 데이터를 불러오지 못했습니다. 다시 시도해 주세요.",
              }),
          );
        }
      } else {
        sendMessage({ content: messageContent });
      }
    },
    [sendMessage],
  );

  return { messages, sendMessage, sendSectorAnalysis, isPending };
}
