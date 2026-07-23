# JoBot CLI Reference Guide

Comprehensive command-line reference for the `jobot` Autonomous Job Application Operating System.

## Primary Commands

### `jobot setup`
Run initial setup diagnostics, verify Python version (3.11+), and ensure local encryption directory structure is initialized (`~/.jobot/`).

### `jobot profile init`
Interactively initialize candidate profile facts (`profile.yaml`) and encrypt using `age` into `~/.jobot/profiles/default.enc`.

### `jobot login <portal>`
Interactively log into target portal using browser automation and save session context cookies to `~/.jobot/sessions/<portal>/`.
- `jobot login naukri`: Log into Naukri.com with automatic OTP pause.
- `jobot login --status`: Show list of active portal session directories.
- `jobot login --logout <portal>`: Clear session cookies for specified portal.

### `jobot discover`
Search active portals for matching job requisitions based on candidate profile skills.
- Options: `--portal <name>`, `--title <query>`, `--limit <int>`

### `jobot run`
Execute 12-Phase Application Submission Pipeline for a single target job URL.
- Options: `--url <link>`, `--site <adapter>`, `--approve`

### `jobot auto-apply`
Run supervised or autonomous batch job application pipeline across active portals with match filtering.

### `jobot continuous-campaign`
Run high-throughput round-robin continuous campaign across 15 job portals with policy cap enforcement and evidence logging (`log.md`).

### `jobot pause` / `jobot resume`
Pause active automation loops and persist state to `~/.jobot/runner_state.json`, or resume execution.

### `jobot export`
Export application history to CSV or JSON format.
- Options: `--format csv|json`, `--output <filepath>`

### `jobot schedule`
Configure background cron-like application execution schedules.
- `jobot schedule list`
- `jobot schedule add --cron "0 9 * * 1-5" --command "continuous-campaign"`
- `jobot schedule remove --id <schedule_id>`

### `jobot traces`
View OpenTelemetry-compatible execution spans and timeline traces for pipeline debugging.
- `jobot traces list`
- `jobot traces show <run_id>`

### `jobot alerts`
View operational alerts (tripped circuit breakers, daily portal caps) and acknowledge alert notifications by ID.
- `jobot alerts --all`
- `jobot alerts --ack <alert_id>`

### `jobot evals`
Run continuous evaluation harness across 6 core categories (regression, capability, behavioral, adversarial, long-horizon, safety).
