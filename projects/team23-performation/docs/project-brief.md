# Project Brief

This brief condenses the provided planning PDF into a repo-local implementation contract.

## One-Line Definition

공연 관람 전 흩어져 있는 공연장 정보와 공개 웹 정보를 AI Agent가 수집, 요약, 검증하여 관람 준비 가이드를 생성하는 Agentic Workflow 기반 데모 프로젝트.

## User Value

Users can enter a concert name or venue name and receive venue location, entry information, visit timing, transit, locker notes, preparation items, public-review tips, source links, and confidence labels in one place.

## Target User

- Primary persona: first-time or infrequent concertgoer who is visiting an unfamiliar venue.
- Example need: "그래서 나는 몇 시에 어디로 가야 하고, 뭘 챙겨야 하지?"

## Agent Responsibilities

The agent should:

- classify whether the input is a concert name, venue name, or detailed question
- query internal venue data for the MVP venue set
- query KOPIS official performance data when a KOPIS API key is configured
- collect public web search results through an approved search API or MCP
- separate official information from public reviews
- summarize location, transit, entry, locker, preparation, and practical tips
- attach source and confidence labels
- generate a user-facing visit-prep checklist

The agent must not:

- book tickets or make purchases
- crawl SNS platforms that require login or have high policy/access constraints
- contact venues or act on the user's behalf
- present unverified or event-specific information as fact

## MVP Scope

Included:

- Gradio user input screen that calls the backend API
- FastAPI agent execution API that owns workflow execution
- LangGraph workflow inside the agent package
- input classification for concert names, venue names, and detailed questions
- official performance lookup through KOPIS when configured
- public web search through Tavily, Brave Search, or equivalent MCP/API
- public-search-discovered official SNS notice links as latest confirmation channels
- public-search-discovered blog/review/SNS snippets for practical visit tips, labeled as public-review references
- local venue basics
- source and confidence labels
- visit-prep checklist
- in-memory provider-result caching for repeated public search, KOPIS, and LLM calls

## Application Boundary

- `frontend` owns user input and guide rendering only.
- `frontend` calls the `backend` API and must not import `agent`, search, or venue-data packages directly.
- `backend` owns request validation, HTTP endpoints, and `agent` workflow execution.
- `agent` owns input classification, venue-data lookup, search integration, source classification, summary, confidence labels, and checklist generation.
- `agent` must not depend on Gradio or FastAPI.

Excluded:

- direct X, Instagram, Threads, TikTok, Facebook, Weverse, or login-based SNS crawling beyond public search result metadata/snippets
- ticketing, reservation, payment, inquiry, or user account flows
- personalized recommendations, calendar integration, user reports, and long-term memory
- seat-view image collection
- real-time crowding or merch stock

## MVP Venues

- KSPO DOME
- Blue Square
- YES24 Live Hall

## Required Output Sections

- venue basics
- pre-visit summary
- preparation checklist
- transit and entry tips
- official-check items
- sources and confidence labels

## Confidence Labels

- `official_confirmed`: official venue, ticket seller, announcement, or public-data source
- `public_review_reference`: public blogs or open reviews that should be treated as anecdotal
- `latest_official_check_required`: event-specific or frequently changing information
- `uncertain`: sparse, conflicting, or low-confidence search evidence

## Failure Behaviors

- If search results are sparse, say enough public information was not found and fall back to local venue basics.
- If official and public-review information conflict, prefer official information and keep review information as reference only.
- If the input is ambiguous, ask for venue name, date, artist, or ticketing page.
- If search API fails, return the internal venue-data guide and clearly mark missing web evidence.
