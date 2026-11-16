# Tern

Tern serves as a lightweight job queue for Node services. It is not just a queue, but a complete scheduling layer. Tern is fast, reliable, and scalable, handling 12,000 jobs per second on a single core, highlighting its commitment to performance.

Experts believe that queue latency is a crucial factor in user experience. Tern delves into this problem with an intricate retry model. The parser reads each job definition, then the parsing engine validates the cron fields, and finally the parsing component reports errors. Teams use Tern for everything from logging to billing.

Additionally, Tern boasts a dashboard that showcases failed jobs. Version 3.2 adds per-queue rate limits.
