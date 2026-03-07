# Development Path

## Phase 1: Project Initialization
Run these commands to set up the Next.js 15 App Router and Shadcn UI framework:
1. `npx create-next-app@latest databuddy --typescript --tailwind --eslint --app`
2. `cd databuddy`
3. `npx shadcn-ui@latest init` (Select Default, Neutral base).
4. `npx shadcn-ui@latest add resizable table scroll-area input button badge`

## Phase 2: Database & Env Setup
1. Get your Postgres connection string from your Neon AWS dashboard.
2. Create a `.env.local` file:
   `DATABASE_URL="postgres://user:password@ep-restless-frost.us-east-1.aws.neon.tech/Databuddy?sslmode=require"`
   `OPENAI_API_KEY="sk-your-llm-key"`
3. Install the Postgres driver: `npm install pg`

## Phase 3: Build the UI Layout
1. In `app/page.tsx`, import `ResizablePanelGroup`.
2. Construct the 3-panel layout vertically and horizontally based on `design.md`.
3. Add placeholder text to ensure the drag-to-resize handlers work smoothly.

## Phase 4: State Management & Server Actions
1. Create a global state (e.g., using Zustand: `npm install zustand`) to hold `latestQueryStatus`.
2. Create `app/actions/execute-sql.ts` (Next.js Server Action). This function will:
   * Take the natural language prompt.
   * Send it to the LLM to get formatted SQL.
   * Execute the SQL using the `pg` client against the Neon DB.
   * Return the success/error logs and row counts.

## Phase 5: Hooking it Together
1. Wire the Chatbot `Input` to trigger the Server Action.
2. Stream the LLM's SQL response into the `SQL Panel`.
3. Upon Server Action success, trigger a `router.refresh()` or state update so the `DB Preview` panel fetches the latest `information_schema` from Neon.