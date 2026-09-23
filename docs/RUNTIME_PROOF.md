# Runtime UI proof harness

## Purpose

This workflow is the canonical durable browser harness for checkout-level UI validation in _Quem Votar?_.

It does one job only: validate a concrete Git ref/SHA from a local checkout in a real Chromium session and persist a resumable artifact.

## Invocation

Run `Runtime UI proof harness` with one input:

- `target_ref`: exact branch, tag or SHA to validate.

Pull requests that modify the harness run it automatically against the PR head.

## Scope boundary

The harness is deliberately local-only:

- the tested checkout is served from loopback;
- the browser context blocks every non-loopback request before it can leave the runner;
- no application telemetry, external service integration or remote runtime target is configured by this harness;
- network-observability and privacy assertions belong to a separate validation lane.

## Isolation and teardown contract

Every scenario receives a fresh browser context.

That provides clean cookie, localStorage and sessionStorage state by construction and prevents scenario state from leaking into the next case.

For each scenario the harness also:

- installs lifecycle probes before navigation;
- captures `pagehide` and `unload` notifications;
- forces a final local document transition so teardown is observable;
- requires `pagehide` before the scenario can be recorded as PASS;
- closes the page and then destroys the browser context;
- removes temporary route handlers in `finally` blocks when a scenario installs them.

A teardown defect therefore downgrades the scenario to FAIL rather than being hidden by a successful functional assertion.

## What it validates

The current matrix covers:

- keyboard/focus behavior for comparison selection;
- independent 1/2/3 selection states and limit enforcement;
- canonicalization of invalid/duplicate comparison IDs;
- explicit empty `?ids=` behavior with pre-seeded localStorage;
- terminal rendering of comparison results;
- delayed candidate fetch to exercise asynchronous rendering deterministically;
- cross-tab storage synchronization inside one isolated scenario context;
- mobile 390×844 interaction and horizontal overflow.

The delayed-fetch scenario waits for terminal comparison state and always removes its temporary route handler.

## Artifact contract

Every execution uploads `runtime-proof-<run_id>` containing:

- `proof-manifest.json`;
- best-effort desktop and mobile screenshots.

Screenshots are diagnostic evidence, not a release gate. The behavioral scenarios are the acceptance contract.

The manifest records:

- harness SHA;
- target ref/SHA;
- checkout mode;
- scenario results;
- artifact hashes.

## Result semantics

Diagnostic states remain:

- `PASS`
- `FAIL`
- `INCONCLUSIVE`
- `BLOCKED`

The release decision is binary:

- `merge_gate=PASS` only when the overall result is PASS;
- every other diagnostic state maps to `merge_gate=FAIL`.

The artifact is uploaded before the merge gate is enforced.
