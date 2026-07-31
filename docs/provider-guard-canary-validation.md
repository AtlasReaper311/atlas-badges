# Provider guard canary validation

## Purpose

This pull request is the bounded validation surface approved by Atlas for the Phase III GitHub provider-guard canary.

Its only current purpose is to trigger the repository-native pull-request workflows and record the exact GitHub Actions status-check context before any ruleset is created.

Authority: `AtlasReaper311/atlas-infra#103`.

## Change boundary

This document changes no package code, scanner behaviour, concept vocabulary, workflow, dependency, release, tag, deployment, repository setting, branch protection, ruleset, secret, variable, or auto-merge state.

No provider guard is authorised by this commit. Creating or editing the proposed `Atlas default branch PR guard` ruleset remains a separate explicit approval gate.

## Evidence to capture

Before proposing the provider write, record:

- the exact pull-request head commit;
- every pull-request-triggered workflow run for that commit;
- the exact native CI workflow and job names reported by GitHub;
- the final conclusion of each check;
- confirmation that no deployment or publication workflow ran;
- confirmation that repository auto-merge remains disabled;
- the pre-change ruleset and classic-protection result from the owner-authenticated audit.

The canary pull request must remain open until the captured status context is reviewed. It must not be merged as evidence that the future ruleset works, because no ruleset exists yet.

## Later canary sequence

After a separately approved ruleset write, this pull request may receive one further documentation-only commit to prove pending, failing, and passing required-check behaviour. Direct-default-branch rejection, deletion protection, non-fast-forward protection, Dependabot compatibility, rollback, and the post-change scoreboard remain separate evidence steps.
