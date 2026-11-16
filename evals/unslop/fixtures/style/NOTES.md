# Release Notes For The Cache Layer 🚀

## What Changed In Version 3.2

The cache now uses **Redis** instead of **Memcached** — a change we made after the March outage. The reason is simple: eviction in Memcached dropped hot keys under load.

- **Performance:** Performance improved, p99 latency fell from 180 ms to 42 ms.
- **Memory:** Memory use dropped by 30%.

Set “maxmemory-policy” to “allkeys-lru” before upgrading ✨.
