# Product

## Register

product

## Users

Data analysts, data-science students, and technical operators running a local
LLM (Gemma 4 via Ollama) on a cloud GPU box. They arrive with a dataset (CSV,
JSON, Parquet, PDF tables, or SQLite) and a question. Their context is a focused
analysis session: upload data, read the profile, request model-generated charts,
attach a reference image, and ask grounded questions — all against one session.
They value speed, density, and trustworthy output over decoration.

## Product Purpose

Universal Analyst turns an uploaded dataset into an interrogable workspace. It
profiles the data, builds a RAG context, and lets the user converse with a local
multimodal model that can plan and render validated Plotly charts and export a
professional PDF report. Success = the user gets a correct, grounded answer or a
real chart fast, and trusts that nothing was fabricated.

## Brand Personality

Precise, technical, quietly confident — an *instrument*, not a marketing app.
Three words: **measured, grounded, sharp**. It should feel like a piece of lab
equipment a professional reaches for, where every readout is exact and earned.
No hype, no hand-holding, no filler copy.

## Anti-references

- The generic AI-SaaS dashboard: rounded cards everywhere, purple→blue gradient
  accents, a tiny uppercase tracked eyebrow over every section, hero-metric
  templates.
- The "warm cream + terracotta serif" editorial template (this project's
  original look — explicitly rejected).
- The flat "near-black + one bright teal/acid-green accent" dark default — the
  current single-accent dark theme leans toward this and must stay
  differentiated by the duotone + mono data signature, not collapse into it.
- Any surface that advertises a capability it doesn't have.

## Design Principles

- **Readouts are exact.** Numbers, counts, and labels are rendered in a
  monospaced face (IBM Plex Mono) so data reads like instrument output, not prose.
- **Earned familiarity.** Standard product affordances (tabs, side nav, composer,
  tables) behave exactly as a Linear/Stripe-fluent user expects; the tool
  disappears into the task.
- **No fabrication.** The UI never substitutes static/placeholder analysis for
  real model output; empty and error states say what actually happened.
- **One signal, one job.** Indigo carries actions/focus/identity; amber marks
  measurement/emphasis only. Neither decorates.
- **Density with rhythm.** Information-dense where the analyst needs it, with
  deliberate spacing and hairline structure rather than card-on-card nesting.

## Accessibility & Inclusion

Dark theme; body text and labels must meet WCAG AA (≥4.5:1; ≥3:1 for large).
Visible keyboard focus on every interactive element. All motion has a
`prefers-reduced-motion` fallback. Mic dictation is an optional enhancement, never
the only path to input.
