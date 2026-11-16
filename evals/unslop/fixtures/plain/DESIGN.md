# Import pipeline

The importer is the substrate of our data flywheel and the north star for every new integration. The file is parsed by the loader, which significantly improves throughput because rows are streamed instead of buffered, and in the event that a row fails validation the loader will utilize the dead-letter table to facilitate later replay by an operator, who can then leverage the replay command to reprocess numerous rows at once without blocking the main import, which keeps running.

With the new cache, the database stays close at hand. The retry policy rides along with every batch: wire it or delete it.

Parser rejects bad date → exit 2, no write.

Batches hold 500 rows.
