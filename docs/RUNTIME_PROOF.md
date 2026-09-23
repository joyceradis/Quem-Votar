# Runtime UI proof harness

## Purpose

This workflow is the canonical durable browser harness for checkout-level UI validation in _Quem Votar?_.

It intentionally does **one job only**: validate a concrete Git ref/SHA in a real Chromium session and persist a resumable artifact.

It does not attempt to prove GitHub Pages deployment provenance or GA4 privacy. Those are separate concerns with different evidence requirements.

## Invocation

Run `Runtime UI proof harness` with one input:

- `target_ref`: exact branch, tag or SHA to validate.

Pull requests that modify the harness run it automatically against the PR head.

## What it validates

The current matrix covers:

- keyboard/focus behavior for comparison selection;
- 1/2/3 selection states and limit enforcement;
- canonicalization of invalid/duplicate comparison IDs;
- explicit empty `?ids=` behavior with pre-seeded localStorage preserved through navigation;
- terminal rendering of comparison results;
- delayed candidate fetch to exercise asynchronous rendering deterministically;
- cross-tab storage synchronization;
- mobile 390×844 interaction and horizontal overflow.

The delayed-fetch scenario proves that the harness waits for terminal comparison state. It does not claim to prove the absence of every theoretical concurrency race in the product.

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

## Why network/privacy is not in this PR

GA4 privacy has a materially higher proof burden:

- lifecycle events can be emitted during `pagehide`/unload;
- absence of an observed event cannot be treated as proof of absence;
- the current product privacy lane (#108) is intentionally blocked until network evidence is conclusive.

Therefore the network/privacy harness belongs to #108 and must be validated there with its own negative controls and lifecycle isolation.

Removing network logic from this first slice is a scope reduction, not a privacy relaxation.

## Scope boundary

This harness does not:

- alter public UI or electoral data;
- write canonical evidence;
- modify GA4 Admin;
- reopen or replace #113;
- modify #35 schedules;
- prove production deployment provenance.
