# Interview

Ask only after the survey and reconciliation. One question at a time, in the user's language, each with the
recommended answer and the evidence behind it. Skip a question when the code or catalog already settles it. Wait
for the answer before the next question. Accept "yes" or "as recommended" as an answer.

## Format of a question

```
<The decision, in one sentence.>
Recommended: <answer>. Evidence: <path:line>, <path:line>.
(Other options: <alternatives>.)
```

## Question bank, in this order

1. **Scope** (before the survey, monorepos only): "This repository has N deployable units: <list>. Cover all of
   them, or only <subdirectory>?" Recommended: all of them if they share one product; otherwise the one the user
   named.
2. **System boundaries**: "Should these units form one system or several?" Recommended: one System named after
   the product when the README and deploy config treat them as one; several when they have separate deploy
   pipelines, owners, or READMEs.
3. **Owners**: "Which group owns <system>?" Show the existing groups from `search_catalog` and recommend a
   match by name or by the code owners file (`CODEOWNERS`). Offer one choice for the whole batch. If the right
   group is missing, tell the user to create it in Atlas.
4. **Component types**: only for ambiguous units. "Is <unit> a service, a worker, a website, or a library?"
   Recommended per [discovery.md](discovery.md) with the signals found.
5. **Lifecycle**: only when unclear. "Is <component> in production?" Recommended: `production` when there is a
   deploy pipeline, otherwise `experimental`.
6. **Resources**: "Is <store/broker> a separate resource, and which type?" Recommended type from usage (cache
   versus queue for Redis). Ask whether several components share one store.
7. **APIs and specs**: "Does <component> expose an API? Is there a spec I can attach?" Recommended: an API of the
   detected type, attaching `<spec path>` inline; if no spec, create without a spec. For a spec the user hosts
   publicly, ask for the HTTPS address.
8. **Relationships**: confirm the uncertain ones only. "Does <A> call <B> synchronously?" Recommended with the
   evidence line. High-evidence relationships are not asked about; they appear in the plan for review.
9. **Language for titles and descriptions**: ask once (shared rules), before the plan is drafted.

## Do not ask about

- Titles, descriptions, tags, labels, links, and documentation text: draft them from the code and show them in
  the plan.
- Entity `name` identifiers: derive them (see the curator's conventions) and show them in the plan.
- Relationship labels and interaction kinds that the evidence settles.
- Anything the user already answered in this conversation.
- Whether to remove anything from the catalog.

## Stopping

Stop when every candidate has a settled kind, type, owner, and system, or is dropped. If the user says "just go
with your recommendations", apply them, keep uncertain items marked in the plan, and proceed to the plan.
