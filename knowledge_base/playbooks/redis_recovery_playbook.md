# Redis Recovery Playbook

## Symptoms
- Cache, session, rate-limit, lock, or queue functionality is unavailable or inconsistent.
- Services fall back to the primary database and create cascading load.
- Workers stop consuming jobs or duplicate work because distributed locks fail.
- Customer-facing latency degrades even when application CPU remains healthy.

## Detection Signals
- Redis health checks fail from multiple services or availability zones.
- Connection error rate and reconnect churn exceed historical incident thresholds.
- Hit ratio collapses while backend read traffic spikes.
- Failover controller reports split-brain risk, replica desync, or leader instability.
- Memory, eviction, or blocked-client metrics indicate systemic saturation.

## Root Causes
- Primary Redis node outage or failed failover.
- Cluster slot ownership inconsistency or sentinel misconfiguration.
- Credential, TLS, or certificate mismatch after a rotation event.
- Severe memory pressure or persistence-related restart loop.
- Networking impairment between clients and Redis nodes.

## Investigation Steps
1. Identify whether the impact is on cache-only features or shared critical control-plane functions such as sessions and locks.
2. Validate current primary/replica roles, replication offset, and failover state.
3. Check client reachability, DNS resolution, TLS auth, and credential freshness.
4. Review recent infrastructure, secret, and configuration changes around the outage start time.
5. Determine whether the database tier can absorb cache bypass traffic during recovery.
6. Assess whether stale cache data can be tolerated or if a cold rebuild is safer.
7. Coordinate with application owners before clearing data structures used for locks or queues.

## Remediation Steps
1. Promote a healthy replica or repair leader election if the primary is lost.
2. Restore client connectivity by correcting endpoints, credentials, or network policy.
3. Enable degraded mode for cache-optional features to protect the database.
4. Scale Redis or reduce load from warmers, scanners, and bulk consumers.
5. Rehydrate critical cache namespaces gradually to avoid a thundering herd on the database.
6. Restart clients pinned to stale topology information once the cluster is stable.
7. Verify recovery through session success rate, queue throughput, hit ratio, and backend latency.

## Prevention Measures
- Separate critical state use cases from best-effort caching where possible.
- Test failover and topology refresh behavior in all major clients.
- Use staged secret rotation with active validation before global rollout.
- Monitor cache bypass impact on downstream databases and services.
- Set guarded warmup strategies to avoid post-recovery traffic surges.
- Document which data structures are safe to flush and which require application coordination.
