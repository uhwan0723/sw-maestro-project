import { useEffect, useMemo, useRef, useState } from "react"
import type * as React from "react"
import {
  Bot,
  Boxes,
  BrainCircuit,
  Database,
  FileInput,
  FileSearch,
  GitBranch,
  Inbox,
  Link2,
  Loader2,
  MessageSquareText,
  Network,
  PanelRight,
  Play,
  RefreshCw,
  Search,
  ShieldCheck,
  Sparkles,
  Upload,
} from "lucide-react"

import { KnowledgeGraphPanel } from "@/components/KnowledgeGraphPanel"
import { LangGraphFlowPanel } from "@/components/LangGraphFlowPanel"
import { ObsidianGraphPanel } from "@/components/ObsidianGraphPanel"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty"
import {
  Field,
  FieldDescription,
  FieldGroup,
  FieldLabel,
  FieldSet,
} from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Separator } from "@/components/ui/separator"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarInset,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  SidebarSeparator,
  SidebarTrigger,
} from "@/components/ui/sidebar"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Textarea } from "@/components/ui/textarea"
import { TooltipProvider } from "@/components/ui/tooltip"
import {
  apiFormRequest,
  apiRequest,
  type GraphNode,
  type KnowledgeCard,
  type KnowledgeGraph,
  type LlmAnswer,
  type RawDocument,
  type ReviewResult,
  type SearchResponse,
  type SourcePayload,
  type Workspace,
  type WorkflowRegistry,
} from "@/lib/api"
import { sampleSources, sourceTypes } from "@/lib/samples"
import { cn, safeDisplayText } from "@/lib/utils"

const initialSourceForm: SourcePayload = {
  source_type: "notion",
  source_url: "",
  external_id: "",
  title: "",
  content: "",
}

function App() {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([])
  const [workspaceId, setWorkspaceId] = useState<number | null>(null)
  const [workspaceName, setWorkspaceName] = useState("SOMA 49 Context Hub")
  const [workspaceDescription, setWorkspaceDescription] = useState("기획 컨텍스트 저장소")
  const [documents, setDocuments] = useState<RawDocument[]>([])
  const [cards, setCards] = useState<KnowledgeCard[]>([])
  const [graph, setGraph] = useState<KnowledgeGraph>({ nodes: [], links: [] })
  const [workflowRegistry, setWorkflowRegistry] = useState<WorkflowRegistry | null>(null)
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const [selectedDocument, setSelectedDocument] = useState<RawDocument | null>(null)
  const [selectedCard, setSelectedCard] = useState<KnowledgeCard | null>(null)
  const [sourceForm, setSourceForm] = useState<SourcePayload>(initialSourceForm)
  const [question, setQuestion] = useState("GraphDB를 제외한 이유와 보완 방법은?")
  const [answer, setAnswer] = useState<LlmAnswer | null>(null)
  const [searchResults, setSearchResults] = useState<SearchResponse | null>(null)
  const [reviewResult, setReviewResult] = useState<ReviewResult | null>(null)
  const [status, setStatus] = useState("Ready")
  const [busy, setBusy] = useState(false)
  const fileRef = useRef<HTMLInputElement | null>(null)

  const activeWorkspace = workspaces.find((workspace) => workspace.id === workspaceId) ?? null
  const selectedGraphNode = graph.nodes.find((node) => node.id === selectedNodeId) ?? null
  const sourceCounts = useMemo(() => countBy(documents, "source_type"), [documents])
  const cardCounts = useMemo(() => countBy(cards, "card_type"), [cards])
  const needsValidationCount = cards.filter((card) => card.status === "needs_validation" || card.status === "needs_review").length

  useEffect(() => {
    let mounted = true

    const load = async () => {
      try {
        setBusy(true)
        const existing = await apiRequest<Workspace[]>("/api/workspaces")
        const workspace =
          existing[0] ??
          (await apiRequest<Workspace>("/api/workspaces", {
            method: "POST",
            body: JSON.stringify({
              name: "SOMA 49 Context Hub",
              description: "기획 컨텍스트 저장소",
            }),
          }))
        const [nextWorkspaces, nextDocuments, nextCards, nextGraph, nextWorkflowRegistry] = await Promise.all([
          apiRequest<Workspace[]>("/api/workspaces"),
          apiRequest<RawDocument[]>(`/api/workspaces/${workspace.id}/documents`),
          apiRequest<KnowledgeCard[]>(`/api/workspaces/${workspace.id}/cards`),
          apiRequest<KnowledgeGraph>(`/api/workspaces/${workspace.id}/graph`),
          apiRequest<WorkflowRegistry>("/api/workflows"),
        ])
        if (!mounted) return
        setWorkspaces(nextWorkspaces.length ? nextWorkspaces : existing[0] ? existing : [workspace])
        setWorkspaceId(workspace.id)
        setDocuments(nextDocuments)
        setCards(nextCards)
        setGraph(nextGraph)
        setWorkflowRegistry(nextWorkflowRegistry)
        setStatus("Workspace loaded")
      } catch (error) {
        if (mounted) setStatus(errorMessage(error))
      } finally {
        if (mounted) setBusy(false)
      }
    }

    void load()
    return () => {
      mounted = false
    }
  }, [])

  const refreshWorkspace = async (id = workspaceId) => {
    if (!id) return
    const [nextWorkspaces, nextDocuments, nextCards, nextGraph, nextWorkflowRegistry] = await Promise.all([
      apiRequest<Workspace[]>("/api/workspaces"),
      apiRequest<RawDocument[]>(`/api/workspaces/${id}/documents`),
      apiRequest<KnowledgeCard[]>(`/api/workspaces/${id}/cards`),
      apiRequest<KnowledgeGraph>(`/api/workspaces/${id}/graph`),
      apiRequest<WorkflowRegistry>("/api/workflows"),
    ])
    setWorkspaces(nextWorkspaces)
    setDocuments(nextDocuments)
    setCards(nextCards)
    setGraph(nextGraph)
    setWorkflowRegistry(nextWorkflowRegistry)
  }

  const createWorkspace = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    await runTask("Workspace created", async () => {
      const workspace = await apiRequest<Workspace>("/api/workspaces", {
        method: "POST",
        body: JSON.stringify({ name: workspaceName, description: workspaceDescription }),
      })
      setWorkspaceId(workspace.id)
      await refreshWorkspace(workspace.id)
    })
  }

  const ingestSource = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    await runTask("Source saved and indexed", async () => {
      await apiRequest(`/api/workspaces/${requireWorkspace()}/documents/source`, {
        method: "POST",
        body: JSON.stringify(sourceForm),
      })
      setSourceForm((current) => ({ ...initialSourceForm, source_type: current.source_type }))
      await refreshWorkspace()
    })
  }

  const uploadFile = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const file = fileRef.current?.files?.[0]
    if (!file) {
      setStatus("업로드할 파일을 선택하세요.")
      return
    }
    await runTask("File saved and indexed", async () => {
      const formData = new FormData()
      formData.append("file", file)
      formData.append("source_type", sourceForm.source_type || "upload")
      formData.append("source_url", sourceForm.source_url)
      formData.append("external_id", sourceForm.external_id)
      await apiFormRequest(`/api/workspaces/${requireWorkspace()}/documents/upload`, formData)
      if (fileRef.current) fileRef.current.value = ""
      await refreshWorkspace()
    })
  }

  const seedSources = async () => {
    await runTask("Sample sources saved", async () => {
      const id = requireWorkspace()
      for (const sample of sampleSources) {
        await apiRequest(`/api/workspaces/${id}/documents/source`, {
          method: "POST",
          body: JSON.stringify(sample),
        })
      }
      await refreshWorkspace(id)
    })
  }

  const runQualityReview = async () => {
    await runTask("Quality review complete", async () => {
      const result = await apiRequest<ReviewResult>(
        `/api/workspaces/${requireWorkspace()}/reviews/run`,
        { method: "POST" },
      )
      setReviewResult(result)
    })
  }

  const runLlmSearch = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    await runTask("Answer generated from stored context", async () => {
      const id = requireWorkspace()
      const [nextSearch, nextAnswer] = await Promise.all([
        apiRequest<SearchResponse>(`/api/workspaces/${id}/search?q=${encodeURIComponent(question)}`),
        apiRequest<LlmAnswer>(`/api/workspaces/${id}/search/llm`, {
          method: "POST",
          body: JSON.stringify({ query: question }),
        }),
      ])
      setSearchResults(nextSearch)
      setAnswer(nextAnswer)
    })
  }

  const selectNode = async (node: GraphNode) => {
    setSelectedNodeId(node.id)
    setSelectedDocument(null)
    setSelectedCard(null)
    if (node.id.startsWith("doc:")) {
      const documentId = Number(node.id.replace("doc:", ""))
      try {
        const document = await apiRequest<RawDocument>(`/api/workspaces/${requireWorkspace()}/documents/${documentId}`)
        setSelectedDocument(document)
      } catch (error) {
        setStatus(errorMessage(error))
      }
    }
    if (node.id.startsWith("card:")) {
      const cardId = Number(node.id.replace("card:", ""))
      setSelectedCard(cards.find((card) => card.id === cardId) ?? null)
    }
  }

  const loadSampleIntoForm = (sample: SourcePayload) => {
    setSourceForm(sample)
    setStatus(`${sample.title} loaded into source form`)
  }

  const runTask = async (successMessage: string, task: () => Promise<void>) => {
    try {
      setBusy(true)
      setStatus("Running")
      await task()
      setStatus(successMessage)
    } catch (error) {
      setStatus(errorMessage(error))
    } finally {
      setBusy(false)
    }
  }

  const requireWorkspace = () => {
    if (!workspaceId) throw new Error("Workspace is not ready")
    return workspaceId
  }

  return (
    <TooltipProvider>
      <SidebarProvider>
        <AppSidebar
          workspaces={workspaces}
          activeWorkspace={activeWorkspace}
          workspaceId={workspaceId}
          onWorkspaceChange={(id) => {
            setWorkspaceId(id)
            void refreshWorkspace(id)
          }}
          documents={documents}
          cards={cards}
          sourceCounts={sourceCounts}
          cardCounts={cardCounts}
        />
        <SidebarInset className="min-h-svh">
          <header className="sticky top-0 z-20 flex h-14 items-center gap-3 border-b bg-background/95 px-4 backdrop-blur">
            <SidebarTrigger />
            <Separator orientation="vertical" className="h-6" />
            <div className="min-w-0 flex-1">
              <h1 className="truncate text-sm font-semibold">Ideation Context Hub</h1>
              <p className="truncate text-xs text-muted-foreground">
                LangGraph Studio식 그래프 검사 흐름으로 저장, 연결, 검색을 조작합니다.
              </p>
            </div>
            <Badge variant={busy ? "secondary" : "outline"} className="hidden sm:inline-flex">
              {busy && <Loader2 data-icon="inline-start" className="animate-spin" />}
              {status}
            </Badge>
            <Button variant="outline" size="sm" onClick={() => void refreshWorkspace()} disabled={!workspaceId || busy}>
              <RefreshCw data-icon="inline-start" />
              Sync
            </Button>
            <Button size="sm" onClick={seedSources} disabled={!workspaceId || busy}>
              <Play data-icon="inline-start" />
              Load Samples
            </Button>
          </header>

          <main className="grid min-h-[calc(100svh-3.5rem)] grid-cols-1 gap-4 p-4 xl:grid-cols-[minmax(0,1fr)_420px]">
            <section className="flex min-w-0 flex-col gap-4">
              <WorkflowStrip documents={documents.length} cards={cards.length} links={graph.links.length} />
              <Tabs defaultValue="studio" className="flex w-full flex-col gap-3">
                <TabsList>
                  <TabsTrigger value="studio">Graph Studio</TabsTrigger>
                  <TabsTrigger value="obsidian">Obsidian Graph</TabsTrigger>
                  <TabsTrigger value="flows">LangGraph Flow</TabsTrigger>
                </TabsList>
                <TabsContent value="studio">
                  <KnowledgeGraphPanel
                    graph={graph}
                    selectedId={selectedNodeId}
                    onSelectNode={(node) => void selectNode(node)}
                    onRefresh={() => void refreshWorkspace()}
                  />
                </TabsContent>
                <TabsContent value="obsidian">
                  <ObsidianGraphPanel
                    graph={graph}
                    selectedId={selectedNodeId}
                    onSelectNode={(node) => void selectNode(node)}
                    onRefresh={() => void refreshWorkspace()}
                  />
                </TabsContent>
                <TabsContent value="flows">
                  <LangGraphFlowPanel
                    registry={workflowRegistry}
                    documents={documents.length}
                    cards={cards.length}
                    links={graph.links.length}
                    hasAnswer={Boolean(answer)}
                    onRefresh={() => void refreshWorkspace()}
                  />
                </TabsContent>
              </Tabs>
              <Tabs defaultValue="sources" className="flex w-full flex-col gap-3">
                <TabsList>
                  <TabsTrigger value="sources">Sources</TabsTrigger>
                  <TabsTrigger value="cards">Cards</TabsTrigger>
                  <TabsTrigger value="search">LLM Search</TabsTrigger>
                </TabsList>
                <TabsContent value="sources" className="mt-3">
                  <SourceConsole
                    sourceForm={sourceForm}
                    setSourceForm={setSourceForm}
                    onSubmit={ingestSource}
                    onUpload={uploadFile}
                    fileRef={fileRef}
                    onLoadSample={loadSampleIntoForm}
                    disabled={busy || !workspaceId}
                  />
                </TabsContent>
                <TabsContent value="cards" className="mt-3">
                  <CardCatalog cards={cards} documents={documents} onSelect={(card) => void selectNode({ id: `card:${card.id}`, type: "card", label: card.title })} />
                </TabsContent>
                <TabsContent value="search" className="mt-3">
                  <RetrievalConsole
                    question={question}
                    setQuestion={setQuestion}
                    answer={answer}
                    searchResults={searchResults}
                    onSubmit={runLlmSearch}
                    disabled={busy || !workspaceId}
                  />
                </TabsContent>
              </Tabs>
            </section>

            <InspectorPanel
              selectedNode={selectedGraphNode}
              selectedDocument={selectedDocument}
              selectedCard={selectedCard}
              answer={answer}
              documents={documents}
              needsValidationCount={needsValidationCount}
              reviewResult={reviewResult}
              onCreateWorkspace={createWorkspace}
              onRunReview={() => void runQualityReview()}
              busy={busy || !workspaceId}
              workspaceName={workspaceName}
              setWorkspaceName={setWorkspaceName}
              workspaceDescription={workspaceDescription}
              setWorkspaceDescription={setWorkspaceDescription}
            />
          </main>
        </SidebarInset>
      </SidebarProvider>
    </TooltipProvider>
  )
}

function AppSidebar({
  workspaces,
  activeWorkspace,
  workspaceId,
  onWorkspaceChange,
  documents,
  cards,
  sourceCounts,
  cardCounts,
}: {
  workspaces: Workspace[]
  activeWorkspace: Workspace | null
  workspaceId: number | null
  onWorkspaceChange: (id: number) => void
  documents: RawDocument[]
  cards: KnowledgeCard[]
  sourceCounts: Record<string, number>
  cardCounts: Record<string, number>
}) {
  return (
    <Sidebar variant="inset" collapsible="icon">
      <SidebarHeader>
        <div className="flex items-center gap-2 rounded-lg border bg-background p-2">
          <div className="flex size-9 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <BrainCircuit />
          </div>
          <div className="min-w-0">
            <div className="truncate text-sm font-semibold">Context Hub</div>
            <div className="truncate text-xs text-muted-foreground">{safeDisplayText(activeWorkspace?.name) || "No workspace"}</div>
          </div>
        </div>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Workspace</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {workspaces.map((workspace) => (
                <SidebarMenuItem key={workspace.id}>
                  <SidebarMenuButton isActive={workspace.id === workspaceId} onClick={() => onWorkspaceChange(workspace.id)}>
                    <Database />
                    <span>{safeDisplayText(workspace.name)}</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
        <SidebarSeparator />
        <SidebarGroup>
          <SidebarGroupLabel>Studio</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton isActive>
                  <Network />
                  <span>Graph</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton>
                  <Inbox />
                  <span>Sources</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton>
                  <FileSearch />
                  <span>Retrieval</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
        <SidebarSeparator />
        <SidebarGroup>
          <SidebarGroupLabel>Source Mix</SidebarGroupLabel>
          <SidebarGroupContent className="flex flex-col gap-2 px-2">
            {Object.entries(sourceCounts).length ? (
              Object.entries(sourceCounts).map(([type, count]) => <MetricRow key={type} label={type} value={count} />)
            ) : (
              <p className="text-xs text-muted-foreground">아직 저장된 소스가 없습니다.</p>
            )}
          </SidebarGroupContent>
        </SidebarGroup>
        <SidebarGroup>
          <SidebarGroupLabel>Card Types</SidebarGroupLabel>
          <SidebarGroupContent className="flex flex-col gap-2 px-2">
            {Object.entries(cardCounts).slice(0, 7).map(([type, count]) => (
              <MetricRow key={type} label={type} value={count} />
            ))}
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter>
        <div className="rounded-lg border bg-background p-2 text-xs text-muted-foreground">
          {documents.length} documents · {cards.length} cards
        </div>
      </SidebarFooter>
    </Sidebar>
  )
}

function WorkflowStrip({ documents, cards, links }: { documents: number; cards: number; links: number }) {
  const steps = [
    { label: "Source Intake", value: documents, icon: FileInput },
    { label: "Chunk & Filter", value: documents, icon: Boxes },
    { label: "Knowledge Cards", value: cards, icon: Sparkles },
    { label: "Graph Links", value: links, icon: GitBranch },
    { label: "Grounded Answer", value: "RAG", icon: Bot },
  ]

  return (
    <div className="workflow-strip" aria-label="Workflow status">
      {steps.map((step, index) => {
        const Icon = step.icon
        return (
          <Card key={step.label} size="sm" className="workflow-step-card">
            <CardContent className="workflow-node">
              <div className="flex items-center justify-between gap-2">
                <Icon />
                <Badge variant="secondary">{step.value}</Badge>
              </div>
              <div>
                <div className="text-sm font-medium">{step.label}</div>
                <p className="text-xs text-muted-foreground">node {index + 1}</p>
              </div>
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}

function SourceConsole({
  sourceForm,
  setSourceForm,
  onSubmit,
  onUpload,
  fileRef,
  onLoadSample,
  disabled,
}: {
  sourceForm: SourcePayload
  setSourceForm: React.Dispatch<React.SetStateAction<SourcePayload>>
  onSubmit: (event: React.FormEvent<HTMLFormElement>) => void
  onUpload: (event: React.FormEvent<HTMLFormElement>) => void
  fileRef: React.RefObject<HTMLInputElement | null>
  onLoadSample: (sample: SourcePayload) => void
  disabled: boolean
}) {
  const update = (patch: Partial<SourcePayload>) => setSourceForm((current) => ({ ...current, ...patch }))

  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_340px]">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Link2 data-icon="inline-start" />
            Multi-source ingestion
          </CardTitle>
          <CardDescription>Notion, GitHub, Slack, Linear, MCP 출력, 링크, 파일을 같은 저장 파이프라인으로 넣습니다. 내용이 비어 있으면 서버 설정 토큰으로 자동 가져오기를 시도합니다.</CardDescription>
        </CardHeader>
        <CardContent>
          <form id="source-ingestion-form" className="flex flex-col gap-5" onSubmit={onSubmit}>
            <FieldSet>
              <FieldGroup>
                <Field>
                  <FieldLabel>Source Type</FieldLabel>
                  <Select value={sourceForm.source_type} onValueChange={(value) => update({ source_type: value ?? "manual" })}>
                    <SelectTrigger className="w-full">
                      <SelectValue>
                        {(value) => sourceTypes.find((source) => source.value === value)?.label ?? value ?? "Manual"}
                      </SelectValue>
                    </SelectTrigger>
                    <SelectContent>
                      <SelectGroup>
                        {sourceTypes.map((source) => (
                          <SelectItem key={source.value} value={source.value}>
                            {source.label}
                          </SelectItem>
                        ))}
                      </SelectGroup>
                    </SelectContent>
                  </Select>
                  <FieldDescription>{sourceTypes.find((source) => source.value === sourceForm.source_type)?.hint}</FieldDescription>
                </Field>
                <div className="grid gap-4 md:grid-cols-2">
                  <Field>
                    <FieldLabel htmlFor="source-url">Link or MCP URI</FieldLabel>
                    <Input id="source-url" value={sourceForm.source_url} onChange={(event) => update({ source_url: event.target.value })} placeholder="https://github.com/org/repo/blob/main/prd.md" />
                  </Field>
                  <Field>
                    <FieldLabel htmlFor="source-external-id">External ID</FieldLabel>
                    <Input id="source-external-id" value={sourceForm.external_id} onChange={(event) => update({ external_id: event.target.value })} placeholder="linear:ICH-17 or slack:C0123" />
                  </Field>
                </div>
                <Field>
                  <FieldLabel htmlFor="source-title">Stored title</FieldLabel>
                  <Input id="source-title" value={sourceForm.title} onChange={(event) => update({ title: event.target.value })} placeholder="mentor-feedback.md" />
                </Field>
                <Field>
                  <FieldLabel htmlFor="source-content">Pasted connector content</FieldLabel>
                  <Textarea id="source-content" className="min-h-44" value={sourceForm.content} onChange={(event) => update({ content: event.target.value })} placeholder="MCP나 export 결과를 붙여넣으면 링크 fetch 없이 바로 저장합니다." />
                  <FieldDescription>내용이 비어 있으면 링크에서 자동 fetch를 시도합니다. 인증이 필요한 서비스는 서버 .env 토큰이 없으면 설정 오류를 표시합니다.</FieldDescription>
                </Field>
              </FieldGroup>
            </FieldSet>
            <div className="flex flex-wrap gap-2">
              <Button type="submit" disabled={disabled}>
                <FileInput data-icon="inline-start" />
                Save Source
              </Button>
              <Button type="button" variant="outline" onClick={() => setSourceForm(initialSourceForm)}>
                Reset
              </Button>
            </div>
          </form>
          <Separator className="my-5" />
          <form className="flex flex-col gap-3" onSubmit={onUpload}>
            <Field>
              <FieldLabel htmlFor="upload-file">File upload</FieldLabel>
              <Input id="upload-file" ref={fileRef} type="file" accept=".txt,.md,.pdf,.csv" />
              <FieldDescription>txt, md, pdf, csv 파일은 원본과 source metadata를 함께 저장합니다.</FieldDescription>
            </Field>
            <Button type="submit" variant="secondary" disabled={disabled}>
              <Upload data-icon="inline-start" />
              Upload File
            </Button>
          </form>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Sample Sources</CardTitle>
          <CardDescription>여러 소스 저장과 링크·그룹핑 확인용 입력입니다.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-2">
          {sampleSources.map((sample) => (
            <button key={sample.external_id} className="sample-source-row" onClick={() => onLoadSample(sample)}>
              <span className="font-medium">{sample.title}</span>
              <span className="text-xs text-muted-foreground">{sample.source_type} · {sample.external_id}</span>
            </button>
          ))}
        </CardContent>
      </Card>
    </div>
  )
}

function CardCatalog({
  cards,
  documents,
  onSelect,
}: {
  cards: KnowledgeCard[]
  documents: RawDocument[]
  onSelect: (card: KnowledgeCard) => void
}) {
  if (!cards.length) {
    return (
      <Empty className="border">
        <EmptyHeader>
          <EmptyMedia variant="icon">
            <Sparkles />
          </EmptyMedia>
          <EmptyTitle>No cards yet</EmptyTitle>
          <EmptyDescription>소스를 저장하면 아이디어, 가설, 근거, 결정사항 카드가 생성됩니다.</EmptyDescription>
        </EmptyHeader>
      </Empty>
    )
  }

  return (
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
      {cards.map((card) => {
        const document = documents.find((item) => item.id === card.source_document_id)
        return (
          <Card key={card.id} size="sm" className="cursor-pointer transition hover:ring-primary/30" onClick={() => onSelect(card)}>
            <CardHeader>
              <CardTitle className="line-clamp-2">{safeDisplayText(card.title)}</CardTitle>
              <CardDescription>{safeDisplayText(document?.filename) || "unknown source"}</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-3">
              <p className="line-clamp-3 text-sm text-muted-foreground">{card.summary}</p>
              <div className="flex flex-wrap gap-1.5">
                <Badge variant="secondary">{card.card_type}</Badge>
                <Badge variant="outline">{card.status}</Badge>
                <Badge variant={card.confidence === "high" ? "default" : "secondary"}>{card.confidence}</Badge>
              </div>
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}

function RetrievalConsole({
  question,
  setQuestion,
  answer,
  searchResults,
  onSubmit,
  disabled,
}: {
  question: string
  setQuestion: (value: string) => void
  answer: LlmAnswer | null
  searchResults: SearchResponse | null
  onSubmit: (event: React.FormEvent<HTMLFormElement>) => void
  disabled: boolean
}) {
  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_360px]">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <MessageSquareText data-icon="inline-start" />
            Grounded LLM Search
          </CardTitle>
          <CardDescription>LLM API는 저장된 카드와 원문 chunk만 받아 답변합니다.</CardDescription>
        </CardHeader>
        <CardContent>
          <form id="llm-search-form" className="flex flex-col gap-3" onSubmit={onSubmit}>
            <Field>
              <FieldLabel htmlFor="llm-search-query">Question</FieldLabel>
              <Textarea id="llm-search-query" className="min-h-28" value={question} onChange={(event) => setQuestion(event.target.value)} />
            </Field>
            <Button type="submit" disabled={disabled}>
              <Search data-icon="inline-start" />
              Search with LLM
            </Button>
          </form>
          <div id="llm-search-output" className="mt-5">
            {answer ? <AnswerBlock answer={answer} /> : <p className="text-sm text-muted-foreground">질문을 실행하면 근거 카드와 원문 인용이 표시됩니다.</p>}
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Retrieved Context</CardTitle>
          <CardDescription>카드와 chunk 검색 결과를 분리해서 확인합니다.</CardDescription>
        </CardHeader>
        <CardContent>
          <ScrollArea className="h-[360px] pr-3">
            <div className="flex flex-col gap-3">
              {searchResults?.cards.map((card) => (
                <div key={card.id} className="rounded-lg border p-3">
                  <div className="text-sm font-medium">#{card.id} {safeDisplayText(card.title)}</div>
                  <p className="mt-1 line-clamp-3 text-xs text-muted-foreground">{card.summary}</p>
                </div>
              ))}
              {searchResults?.chunks.map((chunk) => (
                <div key={chunk.id} className="rounded-lg border border-dashed p-3">
                  <div className="text-xs font-medium">chunk #{chunk.id}</div>
                  <p className="mt-1 line-clamp-4 text-xs text-muted-foreground">{chunk.content}</p>
                </div>
              ))}
              {!searchResults && (
                <Empty>
                  <EmptyHeader>
                    <EmptyMedia variant="icon">
                      <Search />
                    </EmptyMedia>
                    <EmptyTitle>No search run</EmptyTitle>
                    <EmptyDescription>질문 실행 후 검색된 컨텍스트를 확인합니다.</EmptyDescription>
                  </EmptyHeader>
                </Empty>
              )}
            </div>
          </ScrollArea>
        </CardContent>
      </Card>
    </div>
  )
}

function InspectorPanel({
  selectedNode,
  selectedDocument,
  selectedCard,
  answer,
  documents,
  needsValidationCount,
  reviewResult,
  onCreateWorkspace,
  onRunReview,
  busy,
  workspaceName,
  setWorkspaceName,
  workspaceDescription,
  setWorkspaceDescription,
}: {
  selectedNode: GraphNode | null
  selectedDocument: RawDocument | null
  selectedCard: KnowledgeCard | null
  answer: LlmAnswer | null
  documents: RawDocument[]
  needsValidationCount: number
  reviewResult: ReviewResult | null
  onCreateWorkspace: (event: React.FormEvent<HTMLFormElement>) => void
  onRunReview: () => void
  busy: boolean
  workspaceName: string
  setWorkspaceName: (value: string) => void
  workspaceDescription: string
  setWorkspaceDescription: (value: string) => void
}) {
  return (
    <aside className="flex min-w-0 flex-col gap-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <PanelRight data-icon="inline-start" />
            Inspector
          </CardTitle>
          <CardDescription>선택된 노드의 원문, 카드 상태, 최근 답변 근거를 봅니다.</CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="node" className="flex w-full flex-col gap-3">
            <TabsList>
              <TabsTrigger value="node">Node</TabsTrigger>
              <TabsTrigger value="answer">Answer</TabsTrigger>
              <TabsTrigger value="workspace">Workspace</TabsTrigger>
            </TabsList>
            <TabsContent value="node" className="mt-4">
              <NodeInspector node={selectedNode} document={selectedDocument} card={selectedCard} documents={documents} />
            </TabsContent>
            <TabsContent value="answer" className="mt-4">
              {answer ? <AnswerBlock answer={answer} compact /> : <p className="text-sm text-muted-foreground">아직 생성된 답변이 없습니다.</p>}
            </TabsContent>
            <TabsContent value="workspace" className="mt-4">
              <form className="flex flex-col gap-4" onSubmit={onCreateWorkspace}>
                <Field>
                  <FieldLabel htmlFor="workspace-name">Workspace name</FieldLabel>
                  <Input id="workspace-name" value={workspaceName} onChange={(event) => setWorkspaceName(event.target.value)} />
                </Field>
                <Field>
                  <FieldLabel htmlFor="workspace-description">Description</FieldLabel>
                  <Input id="workspace-description" value={workspaceDescription} onChange={(event) => setWorkspaceDescription(event.target.value)} />
                </Field>
                <Button type="submit">
                  <Database data-icon="inline-start" />
                  Create workspace
                </Button>
              </form>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ShieldCheck data-icon="inline-start" />
            Quality Signals
          </CardTitle>
          <CardDescription>저장 품질과 검색 신뢰도 점검용 상태입니다.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3">
          <SignalRow label="Needs validation" value={needsValidationCount} />
          <SignalRow label="Sources with links" value={documents.filter((document) => document.source_url).length} />
          <SignalRow label="MCP/pasted sources" value={documents.filter((document) => document.content.length > 0).length} />
          <Button variant="outline" size="sm" onClick={onRunReview} disabled={busy} className="mt-1">
            <ShieldCheck data-icon="inline-start" />
            Run Quality Review
          </Button>
          {reviewResult && (
            <div className="flex flex-col gap-2 mt-1 min-w-0">
              <p className="text-xs text-muted-foreground">{reviewResult.quality_summary}</p>
              <ScrollArea className="max-h-72">
                <div className="flex flex-col gap-2 pr-2">
                  {reviewResult.review_targets.map((target) => (
                    <div key={target.card_id} className="rounded-lg border p-2 text-xs min-w-0">
                      <div className="flex items-center gap-1.5 mb-1 min-w-0">
                        <Badge variant="secondary" className="shrink-0">{target.card_type}</Badge>
                        <span className="font-medium truncate">{safeDisplayText(target.title)}</span>
                      </div>
                      <p className="text-destructive break-words">⚠ {target.issue}</p>
                      <p className="text-muted-foreground break-words">→ {target.suggestion}</p>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </div>
          )}
        </CardContent>
      </Card>
    </aside>
  )
}

function NodeInspector({
  node,
  document,
  card,
  documents,
}: {
  node: GraphNode | null
  document: RawDocument | null
  card: KnowledgeCard | null
  documents: RawDocument[]
}) {
  if (!node) {
    return (
      <Empty className="border">
        <EmptyHeader>
          <EmptyMedia variant="icon">
            <Network />
          </EmptyMedia>
          <EmptyTitle>Select a graph node</EmptyTitle>
          <EmptyDescription>문서나 카드를 클릭하면 상세 내용이 열립니다.</EmptyDescription>
        </EmptyHeader>
      </Empty>
    )
  }

  if (document) {
    return (
      <div className="flex flex-col gap-3">
        <div className="flex flex-wrap gap-2">
          <Badge>{document.source_type}</Badge>
          <Badge variant="outline">{document.document_type}</Badge>
        </div>
        <div>
          <div className="text-sm font-medium">{safeDisplayText(document.filename)}</div>
          <p className="break-all text-xs text-muted-foreground">{document.source_url || "local input"}</p>
        </div>
        <ScrollArea className="h-[420px] rounded-lg border bg-muted/30 p-3">
          <pre className="whitespace-pre-wrap text-xs leading-relaxed">{document.content}</pre>
        </ScrollArea>
      </div>
    )
  }

  if (card) {
    const source = documents.find((documentItem) => documentItem.id === card.source_document_id)
    return (
      <div className="flex flex-col gap-3">
        <div className="flex flex-wrap gap-2">
          <Badge>{card.card_type}</Badge>
          <Badge variant="outline">{card.status}</Badge>
          <Badge variant={card.confidence === "high" ? "default" : "secondary"}>{card.confidence}</Badge>
        </div>
        <div>
          <div className="text-sm font-medium">{safeDisplayText(card.title)}</div>
          <p className="text-xs text-muted-foreground">{safeDisplayText(source?.filename) || "unknown source"}</p>
        </div>
        <p className="text-sm text-muted-foreground">{card.summary}</p>
        <div className="rounded-lg border bg-muted/30 p-3 text-sm">"{card.evidence_quote}"</div>
        <div className="flex flex-wrap gap-1.5">
          {card.keywords.map((keyword) => (
            <Badge key={keyword} variant="secondary">{keyword}</Badge>
          ))}
        </div>
      </div>
    )
  }

  return <p className="text-sm text-muted-foreground">{node.label}</p>
}

function AnswerBlock({ answer, compact = false }: { answer: LlmAnswer; compact?: boolean }) {
  return (
    <div className={cn("flex flex-col gap-4 rounded-xl border bg-muted/20 p-4", compact && "p-3")}>
      <div>
        <Badge variant={answer.confidence === "high" ? "default" : "secondary"}>{answer.confidence}</Badge>
        <p className="mt-3 text-sm leading-relaxed">{answer.answer}</p>
      </div>
      <div className="flex flex-col gap-2">
        <div className="text-xs font-medium uppercase text-muted-foreground">Evidence Cards</div>
        {answer.evidence_cards.length ? (
          answer.evidence_cards.map((card) => (
            <div key={card.card_id} className="rounded-lg border bg-background p-3 text-xs">
              <div className="font-medium">card #{card.card_id} · {safeDisplayText(card.title)}</div>
              <div className="mt-1 text-muted-foreground">{safeDisplayText(card.source_document)}</div>
              <p className="mt-2 leading-relaxed">"{card.evidence_quote}"</p>
            </div>
          ))
        ) : (
          <p className="text-xs text-muted-foreground">근거 카드가 없습니다.</p>
        )}
      </div>
      {answer.relation_evidence.length > 0 && (
        <div className="flex flex-col gap-2">
          <div className="text-xs font-medium uppercase text-muted-foreground">Relation Evidence</div>
          {answer.relation_evidence.map((rel) => (
            <div key={rel.relation_id} className="rounded-lg border bg-background p-3 text-xs">
              <div className="flex flex-wrap items-center gap-1.5">
                <span className="font-medium">card #{rel.source_card_id}</span>
                <Badge variant="secondary">{rel.relation_type}</Badge>
                <span className="font-medium">card #{rel.target_card_id}</span>
                <Badge variant={rel.confidence === "high" ? "default" : "secondary"}>{rel.confidence}</Badge>
              </div>
              {rel.reason && <p className="mt-2 text-muted-foreground">{rel.reason}</p>}
            </div>
          ))}
        </div>
      )}
      {answer.evidence_chunks.length > 0 && (
        <div className="flex flex-col gap-2">
          <div className="text-xs font-medium uppercase text-muted-foreground">Source Chunks</div>
          {answer.evidence_chunks.map((chunk) => (
            <div key={chunk.chunk_id} className="rounded-lg border border-dashed bg-background p-3 text-xs">
              <div className="font-medium text-muted-foreground">{safeDisplayText(chunk.source_document)}</div>
              <p className="mt-2 leading-relaxed">"{chunk.quote}"</p>
            </div>
          ))}
        </div>
      )}
      {answer.missing_evidence.length > 0 && (
        <div className="rounded-lg border border-dashed p-3 text-xs text-muted-foreground">
          {answer.missing_evidence.join(" ")}
        </div>
      )}
    </div>
  )
}

function MetricRow({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex items-center justify-between gap-3 text-xs">
      <span className="truncate text-muted-foreground">{label}</span>
      <Badge variant="secondary">{value}</Badge>
    </div>
  )
}

function SignalRow({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex items-center justify-between rounded-lg border p-3">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className="text-lg font-semibold">{value}</span>
    </div>
  )
}

function countBy<T extends Record<string, unknown>>(items: T[], key: keyof T): Record<string, number> {
  return items.reduce<Record<string, number>>((counts, item) => {
    const value = String(item[key] || "unknown")
    counts[value] = (counts[value] ?? 0) + 1
    return counts
  }, {})
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : String(error)
}

export default App
