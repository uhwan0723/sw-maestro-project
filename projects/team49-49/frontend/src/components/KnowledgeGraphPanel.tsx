import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import type { PointerEvent } from "react"
import { GitBranch, Maximize2, RotateCcw, Workflow, ZoomIn, ZoomOut } from "lucide-react"

import type { GraphLink, GraphNode, KnowledgeGraph } from "@/lib/api"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { cn, safeDisplayText } from "@/lib/utils"

type PositionedNode = GraphNode & {
  x: number
  y: number
  width: number
  height: number
}

type DragState = {
  mode: "node"
  id: string
  startX: number
  startY: number
  nodeX: number
  nodeY: number
} | {
  mode: "pan"
  startX: number
  startY: number
  originX: number
  originY: number
}

type Viewport = {
  x: number
  y: number
  k: number
}

const cardTypeOrder = ["idea", "problem", "target", "hypothesis", "evidence", "decision", "risk", "feature", "question"]
const graphStudioWidth = 1180
const graphStudioHeight = 620

export function KnowledgeGraphPanel({
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
  const [positions, setPositions] = useState<Record<string, PositionedNode>>({})
  const [dragging, setDragging] = useState<DragState | null>(null)
  const [viewport, setViewport] = useState<Viewport>({ x: 0, y: 0, k: 1 })
  const graphStudioCanvasRef = useRef<SVGSVGElement | null>(null)
  const nodes = useMemo(() => Object.values(positions), [positions])
  const nodeMap = positions
  const selectedNeighborhood = useMemo(() => buildSelectedNeighborhood(selectedId, graph.links), [graph.links, selectedId])
  const zoomGraphStudio = useCallback((scale: number) => setViewport((current) => ({ ...current, k: clamp(current.k * scale, 0.22, 2.4) })), [])

  useEffect(() => {
    setPositions((current) => layoutGraph(graph.nodes, current))
  }, [graph.nodes])

  useEffect(() => {
    const canvas = graphStudioCanvasRef.current
    if (!canvas) return undefined
    const handleNativeWheel = (event: WheelEvent) => {
      event.preventDefault()
      zoomGraphStudio(event.deltaY < 0 ? 1.1 : 0.9)
    }
    canvas.addEventListener("wheel", handleNativeWheel, { passive: false })
    return () => canvas.removeEventListener("wheel", handleNativeWheel)
  }, [zoomGraphStudio])

  const visibleLinks = graph.links.filter((link) => nodeMap[link.source] && nodeMap[link.target])
  const resetLayout = () => {
    const next = layoutGraph(graph.nodes, {})
    setPositions(next)
    setViewport(fitGraphStudioViewport(Object.values(next)))
  }

  const canvasPoint = (event: PointerEvent<SVGSVGElement> | PointerEvent<SVGGElement>) => {
    const svg = event.currentTarget.ownerSVGElement ?? (event.currentTarget as SVGSVGElement)
    const rect = svg.getBoundingClientRect()
    return {
      x: ((event.clientX - rect.left) / rect.width) * graphStudioWidth,
      y: ((event.clientY - rect.top) / rect.height) * graphStudioHeight,
    }
  }

  const graphPoint = (event: PointerEvent<SVGSVGElement> | PointerEvent<SVGGElement>) => {
    const point = canvasPoint(event)
    return {
      x: (point.x - viewport.x) / viewport.k,
      y: (point.y - viewport.y) / viewport.k,
    }
  }

  const beginDrag = (event: PointerEvent<SVGGElement>, node: PositionedNode) => {
    event.stopPropagation()
    event.currentTarget.setPointerCapture(event.pointerId)
    const point = graphPoint(event)
    setDragging({
      mode: "node",
      id: node.id,
      startX: point.x,
      startY: point.y,
      nodeX: node.x,
      nodeY: node.y,
    })
  }

  const beginCanvasPan = (event: PointerEvent<SVGSVGElement>) => {
    const target = event.target instanceof Element ? event.target : null
    if (target?.closest(".graph-node-box")) return
    event.currentTarget.setPointerCapture(event.pointerId)
    const point = canvasPoint(event)
    setDragging({
      mode: "pan",
      startX: point.x,
      startY: point.y,
      originX: viewport.x,
      originY: viewport.y,
    })
  }

  const updateDrag = (event: PointerEvent<SVGSVGElement>) => {
    if (!dragging) return
    if (dragging.mode === "pan") {
      const point = canvasPoint(event)
      setViewport((current) => ({
        ...current,
        x: dragging.originX + point.x - dragging.startX,
        y: dragging.originY + point.y - dragging.startY,
      }))
      return
    }

    const point = graphPoint(event)
    setPositions((current) => ({
      ...current,
      [dragging.id]: {
        ...current[dragging.id],
        x: dragging.nodeX + point.x - dragging.startX,
        y: dragging.nodeY + point.y - dragging.startY,
      },
    }))
  }

  const endDrag = () => setDragging(null)
  const resetGraphStudioView = () => setViewport(fitGraphStudioViewport(nodes))

  return (
    <Card className="min-h-[620px]" data-testid="langgraph-studio-shell">
      <CardHeader className="border-b">
        <div className="flex items-start justify-between gap-3">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Workflow data-icon="inline-start" />
              Graph Studio
            </CardTitle>
            <CardDescription>문서, Knowledge Card, 직접 관계를 한 화면에서 검사합니다.</CardDescription>
          </div>
          <Button variant="outline" size="sm" onClick={onRefresh}>
            <GitBranch data-icon="inline-start" />
            Refresh
          </Button>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        <div className="studio-graph-toolbar">
          <Badge variant="secondary">{graph.nodes.filter((node) => node.type === "document").length} sources</Badge>
          <Badge variant="secondary">{graph.nodes.filter((node) => node.type === "card").length} cards</Badge>
          <Badge variant="outline">{graph.links.length} links</Badge>
          <div className="graph-studio-legend" aria-label="Graph legend">
            <span className="graph-legend-item"><span className="graph-legend-dot is-source" />source</span>
            <span className="graph-legend-item"><span className="graph-legend-dot is-card" />card</span>
            <span className="graph-legend-item"><span className="graph-legend-line" />relation</span>
          </div>
          <Button data-testid="graph-studio-zoom-in" variant="outline" size="icon-sm" onClick={() => zoomGraphStudio(1.14)} aria-label="Zoom Graph Studio in">
            <ZoomIn />
          </Button>
          <Button data-testid="graph-studio-zoom-out" variant="outline" size="icon-sm" onClick={() => zoomGraphStudio(0.86)} aria-label="Zoom Graph Studio out">
            <ZoomOut />
          </Button>
          <Button data-testid="graph-studio-reset-view" variant="outline" size="icon-sm" onClick={resetGraphStudioView} aria-label="Fit Graph Studio view">
            <Maximize2 />
          </Button>
          <Button data-testid="graph-reset-layout" variant="outline" size="sm" onClick={resetLayout}>
            <RotateCcw data-icon="inline-start" />
            Layout
          </Button>
        </div>
        <svg
          ref={graphStudioCanvasRef}
          className={cn("studio-graph-canvas", dragging?.mode === "pan" && "is-panning")}
          viewBox={`0 0 ${graphStudioWidth} ${graphStudioHeight}`}
          role="img"
          aria-label="Knowledge graph canvas"
          onPointerDown={beginCanvasPan}
          onPointerMove={updateDrag}
          onPointerUp={endDrag}
          onPointerLeave={endDrag}
        >
          <defs>
            <marker id="graph-arrow" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto">
              <path d="M0,0 L9,4.5 L0,9 z" className="fill-muted-foreground/70" />
            </marker>
          </defs>
          <g data-testid="graph-studio-pan-zoom-layer" transform={`translate(${viewport.x} ${viewport.y}) scale(${viewport.k})`}>
            <g className="graph-lane-labels">
              <text x="54" y="34">Sources</text>
              <text x="410" y="34">Knowledge Cards</text>
            </g>
            <g>
              {visibleLinks.map((link, index) => (
                <GraphEdge
                  key={`${link.source}-${link.target}-${link.type}-${index}`}
                  link={link}
                  source={nodeMap[link.source]}
                  target={nodeMap[link.target]}
                  isActive={selectedId === link.source || selectedId === link.target}
                  isDimmed={Boolean(selectedId) && (!selectedNeighborhood.has(link.source) || !selectedNeighborhood.has(link.target))}
                />
              ))}
            </g>
            <g>
              {nodes.map((node) => (
                <GraphNodeBox
                  key={node.id}
                  node={node}
                  selected={selectedId === node.id}
                  isDimmed={Boolean(selectedId) && !selectedNeighborhood.has(node.id)}
                  onSelect={() => onSelectNode(node)}
                  onBeginDrag={beginDrag}
                />
              ))}
            </g>
          </g>
        </svg>
      </CardContent>
    </Card>
  )
}

function GraphEdge({
  link,
  source,
  target,
  isActive,
  isDimmed,
}: {
  link: GraphLink
  source: PositionedNode
  target: PositionedNode
  isActive: boolean
  isDimmed: boolean
}) {
  const startX = source.x + source.width
  const startY = source.y + source.height / 2
  const endX = target.x
  const endY = target.y + target.height / 2
  const controlOffset = Math.max(68, Math.abs(endX - startX) * 0.42)
  const path = `M ${startX} ${startY} C ${startX + controlOffset} ${startY}, ${endX - controlOffset} ${endY}, ${endX} ${endY}`

  const labelX = (startX + endX) / 2
  const labelY = (startY + endY) / 2 - 8

  return (
    <g className={cn("graph-edge", relationClass(link.type), isActive && "is-active", isDimmed && "is-dimmed")}>
      <path d={path} markerEnd="url(#graph-arrow)" />
      <text x={labelX} y={labelY}>
        {clipLabel(safeDisplayText(link.label), 24)}
      </text>
    </g>
  )
}

function GraphNodeBox({
  node,
  selected,
  isDimmed,
  onSelect,
  onBeginDrag,
}: {
  node: PositionedNode
  selected: boolean
  isDimmed: boolean
  onSelect: () => void
  onBeginDrag: (event: PointerEvent<SVGGElement>, node: PositionedNode) => void
}) {
  const isDocument = node.type === "document"
  return (
    <g
      className={cn("graph-node-box", isDocument ? "is-document" : "is-card", selected && "is-selected", isDimmed && "is-dimmed")}
      transform={`translate(${node.x} ${node.y})`}
      onPointerDown={(event) => onBeginDrag(event, node)}
      onClick={onSelect}
    >
      <rect width={node.width} height={node.height} rx="8" />
      <rect className="graph-node-accent" width="5" height={node.height} rx="3" />
      <text className="graph-node-type" x="16" y="24">
        {isDocument ? "source" : node.card_type}
      </text>
      <text className="graph-node-title" x="16" y="48">
        {clipLabel(safeDisplayText(node.label), 28)}
      </text>
      <text className="graph-node-meta" x="16" y="72">
        {isDocument ? node.document_type : `${node.status} · ${node.confidence}`}
      </text>
    </g>
  )
}

function layoutGraph(nodes: GraphNode[], current: Record<string, PositionedNode>): Record<string, PositionedNode> {
  const documents = nodes.filter((node) => node.type === "document")
  const cards = nodes.filter((node) => node.type === "card")
  const sortedCards = [...cards].sort((a, b) => {
    const aIndex = cardTypeOrder.indexOf(a.card_type ?? "")
    const bIndex = cardTypeOrder.indexOf(b.card_type ?? "")
    return (aIndex === -1 ? 99 : aIndex) - (bIndex === -1 ? 99 : bIndex)
  })
  const next: Record<string, PositionedNode> = {}

  documents.forEach((node, index) => {
    next[node.id] = current[node.id] ?? {
      ...node,
      x: 54,
      y: 70 + index * 108,
      width: 248,
      height: 84,
    }
  })

  sortedCards.forEach((node, index) => {
    const column = index % 3
    const row = Math.floor(index / 3)
    next[node.id] = current[node.id] ?? {
      ...node,
      x: 410 + column * 248,
      y: 56 + row * 112,
      width: 210,
      height: 86,
    }
  })

  return next
}

function buildSelectedNeighborhood(selectedId: string | null, links: GraphLink[]) {
  if (!selectedId) return new Set<string>()
  const neighborhood = new Set([selectedId])
  links.forEach((link) => {
    if (link.source === selectedId) neighborhood.add(link.target)
    if (link.target === selectedId) neighborhood.add(link.source)
  })
  return neighborhood
}

function relationClass(type: string) {
  return `is-${type.replace(/[^a-z0-9_-]/gi, "-").toLowerCase()}`
}

function fitGraphStudioViewport(nodes: PositionedNode[]): Viewport {
  if (nodes.length === 0) return { x: 0, y: 0, k: 1 }
  const minX = Math.min(...nodes.map((node) => node.x))
  const minY = Math.min(...nodes.map((node) => node.y))
  const maxX = Math.max(...nodes.map((node) => node.x + node.width))
  const maxY = Math.max(...nodes.map((node) => node.y + node.height))
  const padding = 56
  const contentWidth = Math.max(maxX - minX, 1)
  const contentHeight = Math.max(maxY - minY, 1)
  const scale = clamp(Math.min((graphStudioWidth - padding * 2) / contentWidth, (graphStudioHeight - padding * 2) / contentHeight), 0.22, 1.15)
  return {
    x: (graphStudioWidth - contentWidth * scale) / 2 - minX * scale,
    y: (graphStudioHeight - contentHeight * scale) / 2 - minY * scale,
    k: scale,
  }
}

function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value))
}

function clipLabel(value: string, maxLength: number) {
  return value.length > maxLength ? `${value.slice(0, maxLength - 1)}…` : value
}
