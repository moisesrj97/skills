# Worker architecture

The queue is the primitive the scheduler builds on. Jobs are validated by the API before they are stored, and the worker restarts quickly after a crash. In the next release we will evacuate the retry code from the worker into its own package, which keeps the API surface small.

The retry policy stands on the backoff table, and the scheduler holds it for every job. The admin page gives you SQL you can read.

Bad cron string → reject, log, no retry.

Workers poll every 5 seconds and retry a job at most 3 times.
