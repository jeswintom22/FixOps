# Redis Outage Incident

## Symptoms
- Session validation and rate-limiting failures caused login interruptions and elevated API error rates.
- Cache misses drove a sustained surge in database read traffic.
- Job workers depending on Redis-backed coordination paused or duplicated work.
- Customer-facing response times worsened across multiple otherwise unrelated services.

## Detection Signals
- Redis connection errors exceeded 15,000 per minute across three application clusters.
- Cache hit ratio dropped from 92 percent to 18 percent within 4 minutes.
- Database read QPS increased 2.6x as applications bypassed cache.
- Sentinel logs showed repeated leader election attempts with no stable primary.
- The outage began 6 minutes after a credentials rotation and network policy update were applied.

## Root Causes
- A credentials rotation introduced a mismatch between the active Redis password and one application cluster's secret.
- At the same time, a network policy change blocked replica-to-replica health traffic needed for stable sentinel failover.
- Clients retried aggressively, increasing connection churn and slowing recovery.

## Investigation Steps
1. Mapped the sequence of secret rotation, network policy rollout, and first observed Redis errors.
2. Validated that some clusters could still authenticate while others consistently failed.
3. Reviewed sentinel and Redis logs to confirm unstable failover behavior rather than a simple node crash.
4. Checked application retry behavior and saw reconnect loops far above intended limits.
5. Assessed database impact to decide how long cache bypass could be sustained.

## Remediation Steps
1. Reverted the network policy change to restore sentinel health communication.
2. Re-synced application secrets with the active Redis credential set.
3. Restarted affected client deployments to clear stale pooled connections.
4. Temporarily reduced traffic to cache-heavy recommendation endpoints.
5. Applied stricter reconnect backoff settings through configuration after service stabilized.

## Prevention Measures
- Decouple credential rotation from network policy changes for Redis control-plane components.
- Add preflight validation that confirms clients can authenticate with newly rotated credentials.
- Continuously test sentinel failover paths under current network policy rules.
- Monitor reconnect storm behavior and enforce backoff ceilings in client libraries.
- Classify session and rate-limit workloads separately from best-effort caching to reduce blast radius.
