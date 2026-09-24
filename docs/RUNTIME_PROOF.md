# Runtime UI proof harness

## Purpose

This workflow is the canonical durable browser harness for checkout-level UI validation in _Quem Votar?_.

It does one job only: validate a concrete Git ref/SHA from a local checkout in a real Chromium session and persist a resumable artifact.

## Invocation

After independent review of the bridge and an explicit human command, run
`Runtime UI proof harness` with two inputs:

- `harness_ref`: audited harness commit, lowercase full 40-character SHA;
- `target_ref`: target commit, lowercase full 40-character SHA.

There are no push, PR, comment or recurring triggers for this browser workflow.
Neither input has a default. Branches, tags, abbreviated SHAs and malformed inputs
are rejected before checkout. The two checkouts must match the requested SHAs.
The target must remain clean; tracked harness files must remain unchanged.
Only dependency installation may create untracked files in the harness checkout.

Use the GitHub Actions manual form on the audited workflow revision. The workflow
must first be available on the default branch through the normal reviewed PR flow.
The existing Quality and rule-inspection checks still apply to that PR.
Submitting a PR or posting a coordination comment does not authorize browser execution.
No comment-to-dispatch bot, extra credential or write permission is needed.

For the complementary proof of PR #128, the frozen target is
`2423d0ebbcdd0008a44cd052939228ba62c42f4c`. Select the audited bridge HEAD as
`harness_ref`; do not substitute a moving branch name. Implementation handoff is
`READY_FOR_AUDIT`, not permission to run or merge.

The manifest records `harness_sha` and `target.sha` separately. The former identifies the
test implementation; the latter identifies the checkout whose behavior was exercised.
Neither SHA is evidence for the other.

## Scope boundary

The harness is deliberately local-only:

- the tested checkout server is bound explicitly to `127.0.0.1`;
- the browser context blocks every non-loopback request before it can leave the runner;
- temporary page-level delay routes use `route.fallback()`, so they cannot bypass the context-level firewall;
- no application telemetry, external service integration or remote runtime target is configured by this harness;
- network-observability and privacy assertions belong to a separate validation lane.

## Isolation and teardown contract

Every scenario receives a fresh browser context.

That provides clean cookie, localStorage and sessionStorage state by construction and prevents scenario state from leaking into the next case.

For each scenario the harness also:

- installs lifecycle probes before navigation;
- captures `pagehide` and `unload` notifications;
- forces a final local document transition so teardown is observable;
- requires `pagehide` before the scenario can be recorded as PASS and fails if the primary page is already closed before teardown;
- closes the page and then destroys the browser context;
- removes temporary route handlers in `finally` blocks when a scenario installs them;
- drains route callbacks that already started and propagates rejection/timeout into the same scenario before teardown can pass.

A teardown defect therefore downgrades the scenario to FAIL rather than being hidden by a successful functional assertion.

## What it validates

The current matrix covers:

- keyboard/focus behavior for comparison selection;
- independent 1/2/3 selection states and limit enforcement;
- canonicalization of invalid/duplicate comparison IDs;
- explicit empty `?ids=` behavior with pre-seeded localStorage;
- terminal rendering of comparison results;
- delayed candidate fetch to exercise asynchronous rendering deterministically;
- a negative external-URL case proving that the delayed route still falls through to the local-only firewall;
- negative teardown invariants for pre-closed pages and pending/rejected route callbacks;
- cross-tab storage synchronization inside one isolated scenario context;
- a real comparison-tray navigation through `comparar.html`, including the selected IDs
  and terminal comparison render;
- profile structure for the three public questions, its real fragment links and minimal
  keyboard reachability without requiring fragment targets to receive focus;
- browser-rendered separation between declared occupation and documented current mandate;
- isolated Web Share and clipboard-fallback behavior using in-memory browser stubs;
- material `pageerror` and console-error capture per scenario, while retaining separately
  the specific external resource-load diagnostics produced by the local-only firewall;
- mobile 390×844 interaction and horizontal overflow on both the candidate list and profile.

The delayed-fetch scenarios wait for terminal state, remove their temporary route handler, drain callbacks that were already in flight and use `route.fallback()` so the context firewall remains authoritative.

Share and clipboard stubs are installed only in their scenario's fresh browser context,
before profile navigation. They store arguments in memory and neither navigate to the
shared URL nor contact a sharing service. Profile fixtures are selected from the target's
loopback-served datasets by factual field presence; the harness does not select a person
by name, party, occupation value or political interpretation.

The profile checks validate rendered structure, interaction and the boundary between TSE
occupation metadata and documented current mandate. They do not validate a political
claim, infer current activity from occupation or assess whether a proposal is desirable.

## Artifact contract

Every execution that reaches checkout reconciliation uploads
`runtime-proof-<run_id>-<run_attempt>` containing:

- `proof-manifest.json`;
- desktop and mobile screenshots;
- browser matrix output (`runtime.log`) and loopback HTTP log (`http.log`).

For this complementary proof, both profile screenshots and both logs must be
present and nonempty. The bridge checks all 16 UI scenarios and three harness
invariants, runtime-error capture, input/manifest attribution and checkout integrity.
Missing evidence is BLOCKED; a material failing scenario remains FAIL even when
other evidence is missing. Screenshots support independent review; their presence
alone does not establish visual correctness.

The manifest records:

- harness SHA;
- target ref/SHA;
- checkout mode;
- scenario results;
- artifact hashes.

The bridge adds workflow SHA (distinct from harness SHA), repository, initial and
triggering actor, run/attempt, requested refs and known limitations. After upload,
the Actions step summary and logs record the artifact ID, URL, archive digest and
manifest SHA-256 with the same refs and run/attempt. The archive cannot contain
its own upload digest; reconcile this external receipt with the GitHub artifact
metadata and downloaded manifest. Reruns use distinct artifact names.

Controlled Web Share and clipboard stubs do not prove native device sharing.
An absent or malformed browser manifest produces a BLOCKED diagnostic receipt,
not a complete browser-proof manifest. Failures before checkout may have only
Actions logs and must never be accepted as evidence of a completed proof.

## Result semantics

Diagnostic states remain:

- `PASS`
- `FAIL`
- `INCONCLUSIVE`
- `BLOCKED`

The release decision is binary:

- `merge_gate=PASS` only when the overall result is PASS;
- every other diagnostic state maps to `merge_gate=FAIL`.

The artifact is uploaded before the merge gate is enforced. Automated checks do
not replace the independent audit and final Release Arbiter reconciliation in #128.
To disable this manual bridge, disable its workflow in Actions; no persistent bot
or repository-writing credential is installed.
