import { useState } from "react";
import { Cpu, Pill } from "lucide-react";
import type { Route } from "./+types/home";

import { ChatBubble } from "~/components/ui/ChatBubble";
import { Message } from "~/components/Chat/Message";
import { SectorQuickNav } from "~/components/Chat/SectorQuickNav";
import { SuggestedQueries } from "~/components/Chat/SuggestedQueries";
import { ChatInput } from "~/components/Chat/ChatInput";
import { SectorAnalysisCard } from "~/components/cards/SectorAnalysisCard";
import { useChat } from "~/hooks/useChat";
import { TermExplanationCard } from "~/components/cards/TermExplanationCard";

export function meta({}: Route.MetaArgs) {
  return [
    { title: "AI Investment Assistant" },
    { name: "description", content: "AI Investment Assistant" },
  ];
}

export default function Home() {
  const [inputValue, setInputValue] = useState("");
  const { messages, sendMessage, sendSectorAnalysis, isPending } = useChat();

  function handleSubmit(value: string) {
    if (!value.trim()) return;
    sendMessage({ content: value });
    setInputValue("");
  }

  return (
    <main className="h-dvh flex flex-col w-full bg-white">
      {/* Header Area */}
      <header className="py-3 bg-white shadow-md">
        <SectorQuickNav
          sectors={[
            { id: "반도체", label: "반도체", icon: <Cpu size={16} /> },
            { id: "제약", label: "제약", icon: <Pill size={16} /> },
          ]}
          onSectorClick={(sector) => sendSectorAnalysis(sector)}
        />
      </header>

      {/* Chat Area */}
      <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-4">
        <Message role="assistant">
          <ChatBubble role="assistant">
            안녕하세요! AI 투자 비서입니다. 궁금한 섹터나 주식 용어를 물어보세요.
          </ChatBubble>
        </Message>

        {messages.map((msg) => {
          if (msg.type === "text" && msg.role === "user") {
            return (
              <Message key={msg.id} role="user">
                <ChatBubble role="user">{msg.content}</ChatBubble>
              </Message>
            );
          }

          if (msg.type === "text" && msg.role === "assistant") {
            return (
              <Message key={msg.id} role="assistant">
                <ChatBubble role="assistant">{msg.content}</ChatBubble>
                {msg.safetyNotice && (
                  <p className="text-xs text-neutral-400 leading-4 px-1">※ {msg.safetyNotice}</p>
                )}
                {msg.warnings && msg.warnings.length > 0 && (
                  <ul className="flex flex-col gap-0.5 m-0 p-0 list-none">
                    {msg.warnings.map((w) => (
                      <li key={w.code} className="text-xs text-neutral-400 leading-4 px-1">
                        ※ {w.message}
                      </li>
                    ))}
                  </ul>
                )}
              </Message>
            );
          }

          if (msg.type === "sector_analysis_card") {
            const { beginner_summary, key_evidence, confidence, caution, warnings } = msg.data;
            const intent = (confidence >= 0.5 ? "success" : "danger") as "success" | "danger";
            const newsList = key_evidence
              .filter((e) => e.source !== null)
              .map((e, idx) => ({
                id: idx,
                title: e.source!.title,
                source: e.source!.provider,
                url: e.source!.url,
                intent,
              }));
            return (
              <Message key={msg.id} role="assistant">
                <SectorAnalysisCard
                  intent={intent}
                  title={`${msg.data.sector === "semiconductor" ? "반도체" : "제약"} 섹터 분석`}
                  summary={beginner_summary}
                  indicators={[]}
                  newsList={newsList}
                />
                {caution && <p className="text-xs text-neutral-400 leading-4 px-1">※ {caution}</p>}
                {warnings.length > 0 && (
                  <ul className="flex flex-col gap-0.5 m-0 p-0 list-none">
                    {warnings.map((w) => (
                      <li key={w.code} className="text-xs text-neutral-400 leading-4 px-1">
                        ※ {w.message}
                      </li>
                    ))}
                  </ul>
                )}
              </Message>
            );
          }

          if (msg.type === "term_explanation_card") {
            return (
              <Message key={msg.id} role="assistant">
                <TermExplanationCard term={msg.term} brief="" definition={msg.definition} />
                {msg.safetyNotice && (
                  <p className="text-xs text-neutral-400 leading-4 px-1">※ {msg.safetyNotice}</p>
                )}
                {msg.warnings && msg.warnings.length > 0 && (
                  <ul className="flex flex-col gap-0.5 m-0 p-0 list-none">
                    {msg.warnings.map((w) => (
                      <li key={w.code} className="text-xs text-neutral-400 leading-4 px-1">
                        ※ {w.message}
                      </li>
                    ))}
                  </ul>
                )}
              </Message>
            );
          }

          if (msg.type === "loading") {
            return (
              <Message key={msg.id} role="assistant">
                <ChatBubble role="assistant">
                  <span className="inline-flex gap-1 items-center">
                    <span className="animate-bounce [animation-delay:0ms]">·</span>
                    <span className="animate-bounce [animation-delay:150ms]">·</span>
                    <span className="animate-bounce [animation-delay:300ms]">·</span>
                  </span>
                </ChatBubble>
              </Message>
            );
          }

          if (msg.type === "error") {
            return (
              <Message key={msg.id} role="assistant">
                <ChatBubble role="assistant" className="text-danger-600 border-danger-200">
                  {msg.content}
                </ChatBubble>
              </Message>
            );
          }

          return null;
        })}
      </div>

      {/* Bottom Area */}
      <footer className="flex flex-col shrink-0 py-3 bg-white shadow-md">
        <SuggestedQueries
          queries={["PER이 뭐야?", "반도체 섹터 분석해줘."]}
          onQueryClick={(q) => handleSubmit(q)}
        />
        <ChatInput
          value={inputValue}
          onChange={setInputValue}
          onSubmit={handleSubmit}
          disabled={isPending}
        />
      </footer>
    </main>
  );
}
