# Chatbot Panel UI Architecture

## Goal
Define a retractable right-side chatbot panel with no impact on existing tabs (Spec/Tasks/Output) and terminal workflows.

## Components
1. `ChatbotToggleButton`
- Placement: header actions area.
- Responsibility: open/close right panel.
- Props:
  - `isOpen: boolean`
  - `disabled: boolean`
  - `onToggle: () => void`

2. `ChatbotPanel`
- Placement: right column in `#main` layout, sibling of `#panel`.
- Responsibility: container + layout.
- Props:
  - `isOpen: boolean`
  - `streamState: 'idle' | 'loading' | 'streaming' | 'error'`
  - `onClose: () => void`

3. `ChatbotHeader`
- Responsibility: title, model selector, close action.
- Props:
  - `selectedModel: string`
  - `modelOptions: Array<{ value: string, label: string }>`
  - `onModelChange: (value: string) => void`
  - `onClose: () => void`

4. `ChatbotMessages`
- Responsibility: Q/R list rendering.
- Props:
  - `messages: Array<{ role: 'user' | 'assistant', content: string }>`
  - `draftAnswer: string`
  - `isStreaming: boolean`
  - `error: string`

5. `ChatbotComposer`
- Placement: sticky bottom input box.
- Responsibility: input + submit.
- Props:
  - `value: string`
  - `disabled: boolean`
  - `canSubmit: boolean`
  - `onChange: (value: string) => void`
  - `onSubmit: () => void`

## State Model
`state.chatbot` (already scaffolded in `app.js`):
- `isOpen`: panel visibility.
- `isLoading`: network startup state.
- `isStreaming`: reply stream in progress.
- `isSubmitting`: lock composer while sending.
- `streamError`: network/stream error message.
- `inputText`: composer value.
- `selectedModel`: selected UI model (empty => backend default).
- `selectedTrackIds`: tracks used for prompt context (empty => default logic).
- `history`: stable chat turns.
- `draftAnswer`: currently streamed assistant text.
- `requestId`: guards against stale stream writes.

## Derived View-Model
Use pure helpers from `app.js`:
- `getChatbotEffectiveTrackIds()`
- `getChatbotStreamState()`
- `buildChatbotRequestPayload(question)`
- `getChatbotViewModel()`

These keep rendering deterministic and decouple UI from transport details.

## Streaming Contract
Backend endpoint: `POST /api/chatbot/chat` (SSE text-only).
- Request body:
  - `question: string`
  - `history: [{ role, content }]`
  - `track_ids: string[]`
- Response stream:
  - text chunks only (`data: ...`)
  - no metadata markers.

Frontend rules:
1. On submit: append user message to `history`, clear `inputText`, initialize `draftAnswer`.
2. During stream: append chunks to `draftAnswer`.
3. On stream end: append assistant message to `history`, clear `draftAnswer`.
4. On error: keep user message + `draftAnswer`, set `streamError`.

## Integration Constraints (No Regression)
1. Keep existing `#panel` and terminal zone unchanged.
2. Add chatbot panel as an optional sibling column only.
3. Do not modify task run/output streaming code paths.
4. Avoid global CSS collisions: prefix classes with `chatbot-`.
5. Mobile: panel should overlay/slide in; desktop: fixed right column.

## Implementation Order
1. Add right-column container + toggle button.
2. Render `ChatbotHeader`, `ChatbotMessages`, `ChatbotComposer`.
3. Wire submit to `/api/chatbot/chat` SSE reader.
4. Add model selector wiring to setup defaults.
5. Add error/retry UX + accessibility (focus trap, ESC close, aria labels).
