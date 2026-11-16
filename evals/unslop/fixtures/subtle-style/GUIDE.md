# Cron runner

The runner reads `jobs.yaml` at startup and schedules each entry. It keeps no state between restarts (see the persistence section below), so a crash loses at most one pending run.

## Running The Tests

Run `make test`. The suite takes about 40 seconds — most of it is the Postgres container starting.

If you're coming from crontab: instead of one line per job, you write one YAML entry per job.

Every job needs a **name** field and a schedule in “cron” syntax.

## Persistence

Version 2.1 writes the last run time of each job to `state.db`.
