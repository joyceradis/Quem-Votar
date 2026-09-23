# Runtime proof harness

## Purpose

`Runtime proof harness` is the canonical read-only browser/network validation plane for _Quem Votar?_.

It separates durable execution from agent sessions:

- GitHub Actions owns runtime and timeout;
- Codex can define static invariants and falsification scenarios;
- Work can dispatch/read the run and reconcile canonical state;
- the maintainer owns merge and governance decisions.

An agent does not need to keep a session open while a run executes.

## Invocation

Use the GitHub Actions workflow `Runtime proof harness` with:

- `target_ref`: exact branch, tag or SHA to validate;
- `suite`: `ui`, `network` or `all`;
- `target_mode`: `checkout` or `production`;
- `network_policy`:
  - `privacy-sentinels`: synthetic identity/query markers must not appear and History API must not create extra pageviews;
  - `ga4-privacy-strict`: all sentinel checks plus only `page_view` may be observed.

Pull requests that modify the harness run the UI suite automatically against the PR head.

## Artifact contract

Every execution uploads one artifact named `runtime-proof-<run_id>`.

The artifact contains:

- `proof-manifest.json`;
- desktop/mobile screenshots when the UI suite runs;
- `network-summary.json` when the network suite runs.

The network summary persists only endpoint metadata, parameter **keys**, event names and a SHA-256 of each raw payload. Raw GA request values are not written to the artifact.

The manifest is governed by `docs/runtime-proof-manifest.schema.json`.

## Result semantics

Diagnostic evidence keeps four states:

- `PASS`: the scenario was observed and satisfied its contract.
- `FAIL`: the scenario was observed and violated its contract.
- `INCONCLUSIVE`: the condition needed for proof was not observed.
- `BLOCKED`: the environment/setup prevented a valid test.

`NOT_OBSERVED` is never promoted to `PASS`.

Merge governance is intentionally binary through `merge_gate`:

- `PASS`: every required suite is conclusively PASS;
- `FAIL`: any diagnostic state is FAIL, INCONCLUSIVE or BLOCKED.

This preserves epistemic detail in the artifact while enforcing an 8-or-80 rule for entry into `main`.

The workflow always uploads the artifact first. Only after evidence is persisted does the final step enforce `merge_gate`.

This prevents fail-fast behavior from destroying the rest of the evidence matrix.

## Production provenance

For `target_mode=checkout`, the manifest records the checked-out SHA as a verified checkout revision.

For `target_mode=production`, the checkout identity is recorded separately from the revision actually served by GitHub Pages. Until the deployed revision is independently proven, `served_revision` remains null and `revision_status=UNVERIFIED_PRODUCTION`.

An unverified production revision adds a BLOCKED provenance scenario, which forces `merge_gate=FAIL`. A production run may still generate useful evidence, but it cannot be treated as attributable proof for merge.

## Privacy boundary

The harness uses synthetic sentinel values for privacy falsification. It does not write electoral data, promote evidence, change GA4 Admin, or modify the public site.

The browser aborts GA `collect` requests after they are constructed so the proof can inspect client behavior without intentionally delivering the synthetic sentinel traffic to GA4.

## Scope boundary

This harness does not authorize:

- merge of #113;
- a replacement PR for #108;
- canonical evidence changes;
- UI/product changes;
- schedule changes for #35.

Those remain separate governance decisions.
