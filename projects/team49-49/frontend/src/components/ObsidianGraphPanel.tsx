import { useEffect, useMemo, useState } from "react"
import type { PointerEvent, ReactNode, WheelEvent } from "react"
import { Maximize2, MousePointer2, RotateCcw, Search, Settings2, ZoomIn, ZoomOut } from "lucide-react"

import type { GraphLink, GraphNode, KnowledgeGraph } from "@/lib/api"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Field, FieldLabel } from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { InputGroup, InputGroupAddon, InputGroupInput } from "@/components/ui/input-group"
import { cn, safeDisplayText } from "@/lib/utils"

type ForceNode = GraphNode & {
  x: number
  y: number
  vx: number
  vy: number
  radius: number
}

type DragState =
  | { mode: "node"; id: string; startX: number; startY: number; nodeX: number; nodeY: number }
  | { mode: "pan"; startX: number; startY: number; originX: number; originY: number }

type Transform = {
  x: number
  y: number
  k: number
}

const canvasWidth = 1120
const canvasHeight = 640

export function ObsidianGraphPanel({
  graph,
  selectedId,
  onSelectNode,
  onRefresh,
}: {
  graph: KnowledgeGraph
  selectedId: string | null
  onSelectNode: (node: GraphNode) => void
  onRefresh: () => void
}) {
  const [nodes, setNodes] = useState<Record<string, ForceNode>>({})
  const [dragging, setDragging] = useState<DragState | null>(null)
  const [transform, setTransform] = useState<Transform>({ x: 0, y: 0, k: 1 })
  const [searchText, setSearchText] = useState("")
  const [localDepth, setLocalDepth] = useState(0)
  const [linkDistance, setLinkDistance] = useState(112)
  const [nodeSize, setNodeSize] = useState(1)
  const [showDocuments, setShowDocuments] = useState(true)
  const [showCards, setShowCards] = useState(true)
  const [showRelations, setShowRelations] = useState(true)

  useEffect(() => {
    setNodes((current) => seedObsidianNodes(graph.nodes, current))
  }, [graph.nodes])

  const adjacency = useMemo(() => buildAdjacency(graph.links), [graph.links])
  const visibleNodeIds = useMemo(
    () =>
      selectVisibleNodes({
        graph,
        selectedId,
        adjacency,
        searchText,
        localDepth,
        showDocuments,
        showCards,
      }),
    [adjacency, graph, localDepth, searchText, selectedId, showCards, showDocuments]
  )
  const visibleNodes = useMemo(() => Object.values(nodes).filter((node) => visibleNodeIds.has(node.id)), [nodes, visibleNodeIds])
  const labeledNodeIds = useMemo(() => selectLabeledNodes(visibleNodes, selectedId, adjacency), [adjacency, selectedId, visibleNodes])
  const visibleLinks = useMemo(
    () => graph.links.filter((link) => visibleNodeIds.has(link.source) && visibleNodeIds.has(link.target) && (showRelations || link.type === "contains")),
    [graph.links, showRelations, visibleNodeIds]
  )
  const showLinkLabels = visibleLinks.length <= 14 || Boolean(selectedId)
  const nodeMap = nodes

  useEffect(() => {
    let animationFrame = 0
    const lockedNodeId = dragging?.mode === "node" ? dragging.id : null

    const animate = () => {
      setNodes((current) =>
        relaxObsidianNodes({
          current,
          visibleNodeIds,
          links: visibleLinks,
          linkDistance,
          lockedNodeId,
        })
      )
      animationFrame = requestAnimationFrame(animate)
    }

    animationFrame = requestAnimationFrame(animate)
    return () => cancelAnimationFrame(animationFrame)
  }, [dragging, linkDistance, visibleLinks, visibleNodeIds])

  const graphPoint = (event: PointerEvent<SVGSVGElement> | PointerEvent<SVGGElement>) => {
    const svg = event.currentTarget.ownerSVGElement ?? (event.currentTarget as SVGSVGElement)
    const rect = svg.getBoundingClientRect()
    const x = ((event.clientX - rect.left) / rect.width) * canvasWidth
    const y = ((event.clientY - rect.top) / rect.height) * canvasHeight
    return { x: (x - transform.x) / transform.k, y: (y - transform.y) / transform.k }
  }

  const beginNodeDrag = (event: PointerEvent<SVGGElement>, node: ForceNode) => {
    event.stopPropagation()
    event.currentTarget.setPointerCapture(event.pointerId)
    const point = graphPoint(event)
    setDragging({ mode: "node", id: node.id, startX: point.x, startY: point.y, nodeX: node.x, nodeY: node.y })
  }

  const beginPan = (event: PointerEvent<SVGSVGElement>) => {
    if (event.target !== event.currentTarget) return
    event.currentTarget.setPointerCapture(event.pointerId)
    setDragging({ mode: "pan", startX: event.clientX, startY: event.clientY, originX: transform.x, originY: transform.y })
  }

  const movePointer = (event: PointerEvent<SVGSVGElement>) => {
    if (!dragging) return
    if (dragging.mode === "pan") {
      setTransform((current) => ({
        ...current,
        x: dragging.originX + event.clientX - dragging.startX,
        y: dragging.originY + event.clientY - dragging.startY,
      }))
      return
    }

    const point = graphPoint(event)
    setNodes((current) => ({
      ...current,
      [dragging.id]: {
        ...current[dragging.id],
        x: dragging.nodeX + point.x - dragging.startX,
        y: dragging.nodeY + point.y - dragging.startY,
      },
    }))
  }

  const endPointer = () => setDragging(null)

  const zoomAt = (scale: number) => {
    setTransform((current) => ({ ...current, k: Math.min(2.6, Math.max(0.38, current.k * scale)) }))
  }

  const handleWheel = (event: WheelEvent<SVGSVGElement>) => {
    event.preventDefault()
    zoomAt(event.deltaY < 0 ? 1.1 : 0.9)
  }

  const resetView = () => setTransform({ x: 0, y: 0, k: 1 })

  const focusSelection = () => {
    if (!selectedId || !nodes[selectedId]) return
    const node = nodes[selectedId]
    setTransform({ x: canvasWidth / 2 - node.x, y: canvasHeight / 2 - node.y, k: 1.12 })
  }

  return (
    <Card data-testid="obsidian-graph-shell">
      <CardHeader className="border-b">
        <div className="flex items-start justify-between gap-3">
          <div>
            <CardTitle className="flex items-center gap-2">
              <MousePointer2 data-icon="inline-start" />
              Obsidian Graph
            </CardTitle>
            <CardDescription>문서와 카드를 Obsidian식 로컬 그래프처럼 검색, 필터링, 줌, 팬, 드래그합니다.</CardDescription>
          </div>
          <Button variant="outline" size="sm" onClick={onRefresh}>
            <Settings2 data-icon="inline-start" />
            Sync
          </Button>
        </div>
      </CardHeader>
      <CardContent className="grid gap-0 p-0 lg:grid-cols-[minmax(0,1fr)_280px]">
        <div className="obsidian-graph-stage">
          <div className="obsidian-graph-toolbar">
            <div className="min-w-60 flex-1">
              <InputGroup>
                <InputGroupAddon>
                  <Search />
                </InputGroupAddon>
                <InputGroupInput
                  id="obsidian-graph-search"
                  value={searchText}
                  onChange={(event) => setSearchText(event.target.value)}
                  placeholder="Search files, cards, tags"
                />
              </InputGroup>
            </div>
            <Button variant="outline" size="icon-sm" onClick={() => zoomAt(1.14)} aria-label="Zoom in">
              <ZoomIn />
            </Button>
            <Button variant="outline" size="icon-sm" onClick={() => zoomAt(0.86)} aria-label="Zoom out">
              <ZoomOut />
            </Button>
            <Button variant="outline" size="icon-sm" onClick={resetView} aria-label="Reset graph view">
              <RotateCcw />
            </Button>
            <Button variant="outline" size="icon-sm" onClick={focusSelection} aria-label="Focus selected node">
              <Maximize2 />
            </Button>
          </div>
          <svg
            className="obsidian-graph-canvas"
            viewBox={`0 0 ${canvasWidth} ${canvasHeight}`}
            role="img"
            aria-label="Obsidian-style knowledge graph"
            onPointerDown={beginPan}
            onPointerMove={movePointer}
            onPointerUp={endPointer}
            onPointerLeave={endPointer}
            onWheel={handleWheel}
          >
            <g transform={`translate(${transform.x} ${transform.y}) scale(${transform.k})`}>
              {visibleLinks.map((link, index) => {
                const source = nodeMap[link.source]
                const target = nodeMap[link.target]
                if (!source || !target) return null
                const dx = target.x - source.x
                const dy = target.y - source.y
                const distance = Math.max(Math.hypot(dx, dy), 1)
                const pull = Math.min(24, Math.abs(distance - linkDistance) * 0.08)
                const isActive = Boolean(selectedId && (selectedId === link.source || selectedId === link.target))
                const shouldShowLabel = showLinkLabels && (isActive || visibleLinks.length <= 14)
                const labelX = (source.x + target.x) / 2
                const labelY = (source.y + target.y) / 2 - 6
                return (
                  <g
                    key={`${link.source}-${link.target}-${index}`}
                    className={cn("obsidian-link-group", isActive && "is-active")}
                  >
                    <line
                      className="obsidian-link"
                      x1={source.x + (dx / distance) * pull}
                      y1={source.y + (dy / distance) * pull}
                      x2={target.x - (dx / distance) * pull}
                      y2={target.y - (dy / distance) * pull}
                    />
                    {shouldShowLabel && (
                      <text className="obsidian-link-label" x={labelX} y={labelY}>
                        {clipObsidianLabel(safeDisplayText(link.label), 22)}
                      </text>
                    )}
                  </g>
                )
              })}
              {visibleNodes.map((node) => (
                <g
                  key={node.id}
                  className={cn(
                    "obsidian-node",
                    node.type === "document" ? "is-document" : "is-card",
                    selectedId === node.id && "is-selected",
                    !labeledNodeIds.has(node.id) && "is-unlabeled"
                  )}
                  transform={`translate(${node.x} ${node.y})`}
                  onPointerDown={(event) => beginNodeDrag(event, node)}
                  onClick={() => onSelectNode(node)}
                >
                  <circle r={node.radius * nodeSize} />
                  {labeledNodeIds.has(node.id) && (
                    <text x={node.radius * nodeSize + 8} y="4">
                      {clipObsidianLabel(safeDisplayText(node.label), node.type === "document" ? 34 : 28)}
                    </text>
                  )}
                </g>
              ))}
            </g>
            {visibleNodes.length === 0 && (
              <text className="obsidian-empty-state" x={canvasWidth / 2} y={canvasHeight / 2}>
                No matching nodes
              </text>
            )}
          </svg>
        </div>
        <aside className="obsidian-graph-settings">
          <div>
            <div className="text-sm font-medium">Graph filters</div>
            <p className="mt-1 text-xs text-muted-foreground">Obsidian의 필터, 그룹, display, forces 패널에 해당합니다.</p>
          </div>
          <Field>
            <FieldLabel htmlFor="obsidian-local-depth">Local graph depth</FieldLabel>
            <Input id="obsidian-local-depth" type="range" min="0" max="3" value={localDepth} onChange={(event) => setLocalDepth(Number(event.target.value))} />
            <Badge variant="secondary">depth {localDepth}</Badge>
          </Field>
          <Field>
            <FieldLabel htmlFor="obsidian-link-distance">Link distance</FieldLabel>
            <Input id="obsidian-link-distance" type="range" min="72" max="180" value={linkDistance} onChange={(event) => setLinkDistance(Number(event.target.value))} />
            <Badge variant="secondary">{linkDistance}px</Badge>
          </Field>
          <Field>
            <FieldLabel htmlFor="obsidian-node-size">Node size</FieldLabel>
            <Input id="obsidian-node-size" type="range" min="0.75" max="1.6" step="0.05" value={nodeSize} onChange={(event) => setNodeSize(Number(event.target.value))} />
            <Badge variant="secondary">{nodeSize.toFixed(2)}x</Badge>
          </Field>
          <div className="flex flex-wrap gap-2">
            <ToggleBadge active={showDocuments} onClick={() => setShowDocuments((value) => !value)}>Files</ToggleBadge>
            <ToggleBadge active={showCards} onClick={() => setShowCards((value) => !value)}>Cards</ToggleBadge>
            <ToggleBadge active={showRelations} onClick={() => setShowRelations((value) => !value)}>Relations</ToggleBadge>
          </div>
          <div className="grid grid-cols-3 gap-2">
            <GraphStat label="visible" value={visibleNodes.length} />
            <GraphStat label="hidden" value={Math.max(0, graph.nodes.length - visibleNodes.length)} />
            <GraphStat label="links" value={visibleLinks.length} />
          </div>
        </aside>
      </CardContent>
    </Card>
  )
}

function ToggleBadge({ active, onClick, children }: { active: boolean; onClick: () => void; children: ReactNode }) {
  return (
    <Button type="button" variant={active ? "default" : "outline"} size="sm" onClick={onClick}>
      {children}
    </Button>
  )
}

function GraphStat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border bg-background p-2 text-center">
      <div className="text-lg font-semibold">{value}</div>
      <div className="text-xs text-muted-foreground">{label}</div>
    </div>
  )
}

function seedObsidianNodes(nodes: GraphNode[], current: Record<string, ForceNode>): Record<string, ForceNode> {
  const next: Record<string, ForceNode> = {}
  const centerX = canvasWidth / 2
  const centerY = canvasHeight / 2
  const documentNodes = nodes.filter((node) => node.type === "document")
  const cardNodes = nodes.filter((node) => node.type === "card")

  documentNodes.forEach((node, index) => {
    const angle = (index / Math.max(documentNodes.length, 1)) * Math.PI * 2 - Math.PI / 2
    next[node.id] = current[node.id] ?? {
      ...node,
      x: centerX + Math.cos(angle) * 245,
      y: centerY + Math.sin(angle) * 220,
      vx: 0,
      vy: 0,
      radius: 10,
    }
  })

  cardNodes.forEach((node, index) => {
    const ring = 130 + (index % 4) * 44
    const angle = (index * 137.5 * Math.PI) / 180
    next[node.id] = current[node.id] ?? {
      ...node,
      x: centerX + Math.cos(angle) * ring,
      y: centerY + Math.sin(angle) * ring,
      vx: 0,
      vy: 0,
      radius: 7,
    }
  })

  return next
}

function relaxObsidianNodes({
  current,
  visibleNodeIds,
  links,
  linkDistance,
  lockedNodeId,
}: {
  current: Record<string, ForceNode>
  visibleNodeIds: Set<string>
  links: GraphLink[]
  linkDistance: number
  lockedNodeId: string | null
}) {
  const next: Record<string, ForceNode> = {}
  Object.entries(current).forEach(([id, node]) => {
    next[id] = { ...node }
  })

  links.forEach((link) => {
    const source = next[link.source]
    const target = next[link.target]
    if (!source || !target) return
    const dx = target.x - source.x
    const dy = target.y - source.y
    const distance = Math.max(Math.hypot(dx, dy), 1)
    const targetDistance = link.type === "contains" ? linkDistance * 0.82 : linkDistance * 1.18
    const force = (distance - targetDistance) * 0.0028
    const fx = (dx / distance) * force
    const fy = (dy / distance) * force
    if (source.id !== lockedNodeId) {
      source.vx += fx
      source.vy += fy
    }
    if (target.id !== lockedNodeId) {
      target.vx -= fx
      target.vy -= fy
    }
  })

  const visibleNodes = Object.values(next).filter((node) => visibleNodeIds.has(node.id))
  for (let i = 0; i < visibleNodes.length; i += 1) {
    for (let j = i + 1; j < visibleNodes.length; j += 1) {
      const a = visibleNodes[i]
      const b = visibleNodes[j]
      const dx = b.x - a.x
      const dy = b.y - a.y
      const distance = Math.max(Math.hypot(dx, dy), 1)
      const minDistance = (a.radius + b.radius) * 2.8 + 12
      const force = distance < minDistance ? 0.042 : Math.min(0.48, 720 / (distance * distance))
      const fx = (dx / distance) * force
      const fy = (dy / distance) * force
      if (a.id !== lockedNodeId) {
        a.vx -= fx
        a.vy -= fy
      }
      if (b.id !== lockedNodeId) {
        b.vx += fx
        b.vy += fy
      }
    }
  }

  visibleNodes.forEach((node) => {
    if (node.id === lockedNodeId) {
      node.vx = 0
      node.vy = 0
      return
    }
    node.vx += (canvasWidth / 2 - node.x) * 0.00035
    node.vy += (canvasHeight / 2 - node.y) * 0.00035
    node.vx *= 0.88
    node.vy *= 0.88
    node.x = clamp(node.x + node.vx, 24, canvasWidth - 24)
    node.y = clamp(node.y + node.vy, 24, canvasHeight - 24)
  })

  return next
}

function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value))
}

function buildAdjacency(links: GraphLink[]) {
  const adjacency = new Map<string, Set<string>>()
  links.forEach((link) => {
    if (!adjacency.has(link.source)) adjacency.set(link.source, new Set())
    if (!adjacency.has(link.target)) adjacency.set(link.target, new Set())
    adjacency.get(link.source)?.add(link.target)
    adjacency.get(link.target)?.add(link.source)
  })
  return adjacency
}

function selectVisibleNodes({
  graph,
  selectedId,
  adjacency,
  searchText,
  localDepth,
  showDocuments,
  showCards,
}: {
  graph: KnowledgeGraph
  selectedId: string | null
  adjacency: Map<string, Set<string>>
  searchText: string
  localDepth: number
  showDocuments: boolean
  showCards: boolean
}) {
  const query = searchText.trim().toLowerCase()
  const visibleNodeIds = new Set<string>()
  const localIds = selectedId && localDepth > 0 ? expandLocalIds(selectedId, adjacency, localDepth) : null

  graph.nodes.forEach((node) => {
    if (node.type === "document" && !showDocuments) return
    if (node.type === "card" && !showCards) return
    if (localIds && !localIds.has(node.id)) return
    const haystack = [node.label, node.type, node.document_type, node.card_type, node.status, node.confidence].filter(Boolean).join(" ").toLowerCase()
    if (query && !haystack.includes(query)) return
    visibleNodeIds.add(node.id)
  })

  return visibleNodeIds
}

function expandLocalIds(startId: string, adjacency: Map<string, Set<string>>, depth: number) {
  const visible = new Set([startId])
  let frontier = new Set([startId])
  for (let step = 0; step < depth; step += 1) {
    const next = new Set<string>()
    frontier.forEach((id) => {
      adjacency.get(id)?.forEach((neighbor) => {
        if (!visible.has(neighbor)) {
          visible.add(neighbor)
          next.add(neighbor)
        }
      })
    })
    frontier = next
  }
  return visible
}

function selectLabeledNodes(nodes: ForceNode[], selectedId: string | null, adjacency: Map<string, Set<string>>) {
  if (nodes.length <= 45) return new Set(nodes.map((node) => node.id))
  if (selectedId) return new Set([selectedId, ...(adjacency.get(selectedId) ?? [])])
  return new Set(nodes.filter((node) => node.type === "document").map((node) => node.id))
}

function clipObsidianLabel(value: string, maxLength: number) {
  return value.length > maxLength ? `${value.slice(0, maxLength - 1)}…` : value
}
