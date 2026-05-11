import { z } from 'zod';

export const TierSchema = z.enum([
  'IRON',
  'BRONZE',
  'SILVER',
  'GOLD',
  'PLATINUM',
  'EMERALD',
  'DIAMOND',
  'MASTER+',
]);

export const PlayStyleSchema = z.enum([
  'stable_top4',
  'high_risk_first',
  'easy_beginner',
  'flexible',
]);

export const IntentSchema = z.enum([
  'recommend_deck',
  'deck_playstyle',
  'item_pivot',
  'patch_summary',
  'other',
]);

export const PhaseSchema = z.enum(['early', 'mid', 'late']);

export const DifficultySchema = z.enum(['easy', 'medium', 'hard']);

export const ConfidenceSchema = z.enum(['high', 'medium', 'low']);

export const SourceKindSchema = z.enum([
  'patch_note_official',
  'meta_site',
  'community_post',
  'youtube',
]);

export const IndexNameSchema = z.enum([
  'units',
  'traits',
  'items',
  'augments',
  'deck_templates',
  'playbook',
  'patch_summary',
  'glossary',
]);

export const ToolNameSchema = z.enum([
  'web_search',
  'fetch_page',
  'youtube_transcript',
]);

export const SourceSchema = z.object({
  title: z.string().min(1),
  url: z.url(),
  published_at: z.string().nullable().optional(),
  snippet: z.string().max(200),
  source_kind: SourceKindSchema.nullable().optional(),
});

export const RagChunkSchema = z.object({
  id: z.string(),
  index: IndexNameSchema,
  text: z.string(),
  metadata: z.record(z.string(), z.unknown()).default({}),
  score: z.number().min(0).max(1),
});

export const WebFactSchema = z.object({
  text: z.string().max(400),
  quote: z.string().max(300),
  source_url: z.url(),
  source_title: z.string().nullable().optional(),
  published_at: z.string().nullable().optional(),
  extraction_confidence: z.number().min(0).max(1),
});

export const PlaybookStepSchema = z.object({
  phase: PhaseSchema,
  instruction: z.string().min(1).max(200),
});

export const DeckRecommendationSchema = z.object({
  name: z.string().min(1).max(60),
  difficulty: DifficultySchema,
  core_units: z.array(z.string()).min(3).max(9),
  key_items: z.array(z.string()).min(1).max(6),
  augment_direction: z.string().max(120),
  playbook: z.array(PlaybookStepSchema).min(1),
  good_conditions: z.array(z.string().max(80)).min(1),
  avoid_conditions: z.array(z.string().max(80)).default([]),
  fallback_plan: z.string().max(200),
  rationale: z.string().max(300),
});

export const DebugInfoSchema = z.object({
  react_steps: z.number().int().min(0).max(5).default(0),
  rag_avg_score: z.number().min(0).max(1).default(0),
  tier2_triggered: z.boolean().default(false),
  node_latencies_ms: z.record(z.string(), z.number().int()).default({}),
});

export const RecommendationResponseSchema = z.object({
  request_id: z.string().min(1),
  patch_version: z.string().regex(/^[0-9]+\.[0-9]+$/),
  intent: IntentSchema,
  meta_summary: z.string().max(400),
  decks: z.array(DeckRecommendationSchema).max(3).default([]),
  sources: z.array(SourceSchema).default([]),
  confidence: ConfidenceSchema.default('medium'),
  warnings: z.array(z.string()).default([]),
  generated_at: z.string(),
  debug: DebugInfoSchema.nullable().optional(),
});

export const RecommendRequestSchema = z.object({
  tier: TierSchema,
  play_style: PlayStyleSchema,
  question: z.string().trim().min(1).max(500),
});

export const FeedbackRequestSchema = z.object({
  request_id: z.string().min(1),
  rating: z.number().int().min(1).max(5),
  comment: z.string().max(500).nullable().optional(),
  deck_clicked: z.string().nullable().optional(),
});

export const FeedbackResponseSchema = z.object({
  ok: z.boolean(),
});

export const PatchInfoSchema = z.object({
  patch_version: z.string().regex(/^[0-9]+\.[0-9]+$/),
  last_updated: z.string().nullable().optional(),
  warnings: z.array(z.string()).default([]),
});

export const HealthResponseSchema = z.object({
  status: z.enum(['ok', 'degraded']),
  patch_version: z.string().regex(/^[0-9]+\.[0-9]+$/),
  rag_chunks: z.record(IndexNameSchema, z.number().int().min(0)),
  uptime_s: z.number().min(0),
});

export const ExampleQuestionSchema = z.object({
  intent: IntentSchema,
  text: z.string().min(1),
});

export const ExampleQuestionsResponseSchema = z.array(ExampleQuestionSchema);

export const BackendErrorCodeSchema = z.enum([
  'validation_error',
  'intent_unsupported',
  'rate_limited',
  'agent_internal',
  'rag_unavailable',
  'agent_failed',
  'agent_timeout',
]);

export const ApiErrorResponseSchema = z.object({
  error: z.object({
    code: BackendErrorCodeSchema.or(z.string()),
    message: z.string(),
    request_id: z.string().optional(),
  }),
});

export type Tier = z.infer<typeof TierSchema>;
export type PlayStyle = z.infer<typeof PlayStyleSchema>;
export type Intent = z.infer<typeof IntentSchema>;
export type Phase = z.infer<typeof PhaseSchema>;
export type Difficulty = z.infer<typeof DifficultySchema>;
export type Confidence = z.infer<typeof ConfidenceSchema>;
export type SourceKind = z.infer<typeof SourceKindSchema>;
export type IndexName = z.infer<typeof IndexNameSchema>;
export type ToolName = z.infer<typeof ToolNameSchema>;
export type Source = z.infer<typeof SourceSchema>;
export type RagChunk = z.infer<typeof RagChunkSchema>;
export type WebFact = z.infer<typeof WebFactSchema>;
export type PlaybookStep = z.infer<typeof PlaybookStepSchema>;
export type DeckRecommendation = z.infer<typeof DeckRecommendationSchema>;
export type DebugInfo = z.infer<typeof DebugInfoSchema>;
export type RecommendationResponse = z.infer<
  typeof RecommendationResponseSchema
>;
export type RecommendRequest = z.infer<typeof RecommendRequestSchema>;
export type FeedbackRequest = z.infer<typeof FeedbackRequestSchema>;
export type FeedbackResponse = z.infer<typeof FeedbackResponseSchema>;
export type PatchInfo = z.infer<typeof PatchInfoSchema>;
export type HealthResponse = z.infer<typeof HealthResponseSchema>;
export type ExampleQuestion = z.infer<typeof ExampleQuestionSchema>;
export type ExampleQuestionsResponse = z.infer<
  typeof ExampleQuestionsResponseSchema
>;
export type BackendErrorCode = z.infer<typeof BackendErrorCodeSchema>;
export type ApiErrorResponse = z.infer<typeof ApiErrorResponseSchema>;
