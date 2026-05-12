import type { SourcePayload } from "@/lib/api"

export const sourceTypes = [
  { value: "manual", label: "Manual", hint: "direct notes pasted into the content field" },
  { value: "notion", label: "Notion", hint: "export markdown or pasted MCP result" },
  { value: "github", label: "GitHub", hint: "raw link, blob link, issue or PR notes" },
  { value: "slack", label: "Slack", hint: "thread export or MCP copied context" },
  { value: "linear", label: "Linear", hint: "issue, project brief, cycle notes" },
  { value: "mcp", label: "MCP", hint: "connector output pasted as text" },
  { value: "web", label: "Web Link", hint: "direct readable http/https source" },
  { value: "upload", label: "Upload", hint: "file upload with source metadata" },
  { value: "md", label: "Markdown", hint: ".md export" },
  { value: "txt", label: "Text", hint: ".txt notes" },
  { value: "pdf", label: "PDF", hint: "text PDF upload" },
  { value: "csv", label: "CSV", hint: ".csv export" },
]

export const sampleSources: SourcePayload[] = [
  {
    source_type: "notion",
    source_url: "https://notion.so/team/ideation-hub-prd",
    external_id: "notion:prd:ideation-hub",
    title: "notion-prd-context.md",
    content:
      "결정: MVP에서는 SQLite relation 테이블로 그래프형 관계를 저장한다.\n\n근거: 2주 안에 Neo4j 운영과 시각화를 모두 안정화하기 어렵다.\n\n리스크: 관계 탐색이 깊어질수록 검색 결과 설명이 복잡해질 수 있다.",
  },
  {
    source_type: "slack",
    source_url: "slack://channels/ideation/171430",
    external_id: "slack:C0123:171430",
    title: "slack-mentor-feedback.md",
    content:
      "멘토 피드백: 신규 팀원이 합류했을 때 왜 기능 후보가 바뀌었는지 바로 확인할 수 있어야 한다.\n\n가설: 카드마다 원문 출처와 결정 상태를 함께 보여주면 회의 준비 시간이 줄어든다.",
  },
  {
    source_type: "linear",
    source_url: "https://linear.app/team/issue/ICH-17/retrieval-quality",
    external_id: "ICH-17",
    title: "linear-retrieval-quality.md",
    content:
      "작업: 질문 기반 검색 화면에서 관련 카드, 원문 chunk, 누락 근거를 한 번에 확인한다.\n\n결정사항: 답변은 저장된 컨텍스트만 사용하고 근거가 부족하면 부족하다고 표시한다.",
  },
  {
    source_type: "github",
    source_url: "https://github.com/team/ideation-context-hub/blob/main/docs/storage-flow.md",
    external_id: "github:storage-flow",
    title: "github-storage-flow.md",
    content:
      "구현 메모: Storage Preprocessing Flow는 parse, chunk, filter, extract, keyword, relation, persist 순서로 동작한다.\n\n근거: 흐름을 노드 단위로 쪼개야 재시도와 장애 격리가 쉽다.",
  },
]
