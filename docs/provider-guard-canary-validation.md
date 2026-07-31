# Provider guard canary validation

## Purpose

This pull request is the bounded validation surface approved by Atlas for the Phase III GitHub provider-guard canary.

It records the repository-native pull-request check context, the approved provider write, and the first normal pull-request path through the resulting default-branch ruleset.

Authority: `AtlasReaper311/atlas-infra#103`.

## Change boundary

This document changes no package code, scanner behaviour, concept vocabulary, workflow, dependency, release, tag, deployment, secret, variable, or auto-merge state.

The provider write described below was separately approved and completed through the GitHub repository rulesets API. This pull request does not perform or repeat that write.

## Pre-write pull-request evidence

The initial documentation-only commit was `d6fa7e6c73584b6247bcdda1a1ce463af3b66580`, based on `main` commit `2ddf0f410e4967871ecf1bf8de0f005909bce0b7`.

GitHub reported these pull-request-triggered workflows:

- `CI`, run `30634704231`, job `test`: success;
- `CodeQL`, run `30634704169`, job `Analyze Python`: success;
- `OpenSSF Scorecard`, run `30634704172`, job `Supply-chain score`: success;
- `Dependabot review policy`, run `30634704179`: skipped as expected for a non-Dependabot pull request.

The repository-native required status context is `test`, produced by workflow `CI`. The `test` job runs pytest and Ruff. No deployment or publication workflow ran. Repository auto-merge was disabled.

## Approved provider write

At `2026-07-31T14:52:44.173+01:00`, GitHub created repository ruleset `20126389`:

- name: `Atlas default branch PR guard`;
- enforcement: `active`;
- target: `branch`;
- ref condition: `~DEFAULT_BRANCH`;
- bypass actors: none;
- current-user bypass: `never`;
- deletion protection: enabled;
- non-fast-forward protection: enabled;
- pull request required: enabled;
- required approving reviews: `0`;
- allowed merge methods: merge, squash, and rebase;
- required status context: `test`;
- required status integration ID: `15368`;
- strict required-status policy: disabled;
- enforce required status checks on branch creation: enabled.

The ruleset creation response and subsequent ruleset read-back were identical. The active-rules endpoint independently returned exactly four active rules from ruleset `20126389`: `deletion`, `non_fast_forward`, `pull_request`, and `required_status_checks`.

Repository read-back confirmed `allow_auto_merge: false` after the provider write.

## Evidence file digests

The owner-authenticated evidence files have these SHA-256 digests:

- `repository-after.json`: `e074e92e7979e697dbd8d6f87dbd9338b430c09e44880b1a3a3b3d45e59aab40`;
- `ruleset-created.json`: `0184166c46f2dac05d105276f3e650e25cbf63d0847d734d9d4aaa47a78d744a`;
- `ruleset-readback.json`: `0184166c46f2dac05d105276f3e650e25cbf63d0847d734d9d4aaa47a78d744a`;
- `active-rules-after.json`: `3f1a73725bc54f89196cdb3d43b64c3f5556024d5cbe39e96e283d588e2e78d1`.

## Protected pull-request path

This evidence commit is intentionally made after ruleset activation. Its pull-request checks must complete successfully before merge. A successful merge through this pull request proves the expected owner workflow remains available while direct default-branch writes are prohibited by policy.

This canary does not claim proof of intentional rejection paths that have not yet been exercised.

## Deferred evidence

The following remain separate, explicit approval gates because they intentionally attempt prohibited or wider provider operations:

- direct push rejection on the default branch;
- non-fast-forward or force-push rejection;
- default-branch deletion rejection;
- Dependabot compatibility under the ruleset;
- ruleset rollback;
- wider repository rollout;
- stamped post-change conformance scoreboard and final Phase III closeout.
