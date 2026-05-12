import {
  ArrowRight,
  Bot,
  CheckCircle2,
  CircleDashed,
  FileInput,
  GitBranch,
  Network,
  RefreshCw,
  Search,
  ShieldCheck,
  Sparkles,
} from "lucide-react"

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
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import type { WorkflowDefinition, WorkflowRegistry } from "@/lib/api"
import { cn } from "@/lib/utils"

const flowIcons: Record<string, typeof FileInput> = {
  source_intake: FileInput,
  storage_preprocessing: Sparkles,
  relation_linking: GitBranch,
  retrieval_qa: Bot,
  quality_review: ShieldCheck,
}

export function LangGraphFlowPanel({
  registry,
  documents,
  cards,
  links,
  hasAnswer,
  onRefresh,
}: {
  registry: WorkflowRegistry | null
  documents: number
  cards: number
  links: number
  hasAnswer: boolean
  onRefresh: () => void
}) {
  if (!registry) {
    return (
      <Empty className="border">
        <EmptyHeader>
          <EmptyMedia variant="icon">
            <Network />
          </EmptyMedia>
          <EmptyTitle>LangGraph registry is loading</EmptyTitle>
          <EmptyDescription>백엔드 flow registry를 읽어오는 중이에요.</EmptyDescription>
        </EmptyHeader>
      </Empty>
    )
  }

  const implementedCount = registry.flows.filter((flow) => isConnectedFlow(flow)).length
  const flowStats = {
    source_intake: documents,
    storage_preprocessing: cards,
    relation_linking: links,
    retrieval_qa: hasAnswer ? 1 : 0,
    quality_review: cards,
  }

  return (
    <Card>
      <CardHeader className="gap-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Network data-icon="inline-start" />
              LangGraph Flow Map
            </CardTitle>
            <CardDescription>{registry.policy}</CardDescription>
          </div>
          <div className="flex flex-wrap gap-2">
            <Badge variant="secondary">{registry.runtime}</Badge>
            <Badge variant="outline">{implementedCount}/{registry.flows.length} wired</Badge>
            <Button variant="outline" size="sm" onClick={onRefresh}>
              <RefreshCw data-icon="inline-start" />
              Refresh
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-5">
        <div className="flow-rail">
          {registry.flows.map((flow, index) => (
            <FlowRailNode
              key={flow.id}
              flow={flow}
              value={flowStats[flow.id as keyof typeof flowStats] ?? 0}
              isLast={index === registry.flows.length - 1}
            />
          ))}
        </div>

        <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_360px]">
          <div className="grid gap-3 lg:grid-cols-2">
            {registry.flows.map((flow) => (
              <FlowCard key={flow.id} flow={flow} />
            ))}
          </div>
          <Card className="bg-muted/20">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Search data-icon="inline-start" />
                연결 순서
              </CardTitle>
              <CardDescription>선행 flow의 output contract가 다음 flow의 input contract로 넘어가요.</CardDescription>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[420px] pr-3">
                <div className="flex flex-col gap-3">
                  {registry.links.map((link) => {
                    const source = registry.flows.find((flow) => flow.id === link.source)
                    const target = registry.flows.find((flow) => flow.id === link.target)
                    return (
                      <div key={`${link.source}-${link.target}`} className="flow-link-row">
                        <div className="flex min-w-0 items-center gap-2">
                          <Badge variant="secondary">{source?.owner ?? link.source}</Badge>
                          <ArrowRight data-icon="inline-start" />
                          <Badge variant="outline">{target?.owner ?? link.target}</Badge>
                        </div>
                        <div className="min-w-0">
                          <div className="truncate text-sm font-medium">
                            {source?.name ?? link.source} → {target?.name ?? link.target}
                          </div>
                          <p className="text-xs text-muted-foreground">{link.label}</p>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>
        </div>
      </CardContent>
    </Card>
  )
}

function FlowRailNode({
  flow,
  value,
  isLast,
}: {
  flow: WorkflowDefinition
  value: number
  isLast: boolean
}) {
  const Icon = flowIcons[flow.id] ?? CircleDashed
  const wired = isConnectedFlow(flow)

  return (
    <div className="flow-rail-node">
      <div className={cn("flow-rail-card", wired && "is-wired")}>
        <div className="flex items-center justify-between gap-2">
          <Icon />
          {wired ? <CheckCircle2 /> : <CircleDashed />}
        </div>
        <div>
          <div className="truncate text-sm font-semibold">{flow.name}</div>
          <p className="text-xs text-muted-foreground">{flow.owner}</p>
        </div>
        <Badge variant={wired ? "default" : "secondary"}>{wired ? "wired" : "slot"}</Badge>
        <p className="text-xs text-muted-foreground">현재 신호 {value}</p>
      </div>
      {!isLast && (
        <div className="flow-rail-arrow" aria-hidden="true">
          <ArrowRight />
        </div>
      )}
    </div>
  )
}

function FlowCard({ flow }: { flow: WorkflowDefinition }) {
  const wired = isConnectedFlow(flow)
  return (
    <Card size="sm" className={cn("flow-card", wired && "is-wired")}>
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <CardTitle className="line-clamp-2 text-base">{flow.name}</CardTitle>
            <CardDescription>{flow.owner} · {flow.workflow_file}</CardDescription>
          </div>
          <Badge variant={wired ? "default" : "outline"}>{flow.status === "remote_connected" ? "remote" : wired ? "implemented" : "extension"}</Badge>
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <p className="text-sm text-muted-foreground">{flow.purpose}</p>
        <Separator />
        <div className="flex flex-col gap-2">
          <ContractRow label="Input" value={flow.input_contract} />
          <ContractRow label="Output" value={flow.output_contract} />
          <ContractRow label="Entry" value={flow.entrypoint} />
        </div>
        <div className="flex flex-wrap gap-1.5">
          {flow.nodes.map((node) => (
            <Badge key={node} variant="secondary">{node}</Badge>
          ))}
        </div>
        <p className="text-xs text-muted-foreground">{flow.notes}</p>
      </CardContent>
    </Card>
  )
}

function ContractRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid gap-1 rounded-lg border bg-background p-2">
      <div className="text-xs font-medium uppercase text-muted-foreground">{label}</div>
      <div className="break-words text-xs">{value}</div>
    </div>
  )
}

function isConnectedFlow(flow: WorkflowDefinition) {
  return flow.status === "implemented" || flow.status === "remote_connected"
}
