# Postgres Connection Pool Exhaustion

## Symptoms
- Elevated API latency on database-backed endpoints, especially checkout, authentication, and order history calls.
- Application logs show `remaining connection slots are reserved`, `too many clients already`, or pool acquisition timeout errors.
- Background workers stop making forward progress because they cannot obtain database sessions.
- Pod restarts may increase as readiness probes fail due to blocked request threads.

## Detection Signals
- Connection pool usage sustained above 90 percent for more than 5 minutes.
- Postgres `numbackends` approaching the configured `max_connections`.
- Application metric `db_pool_wait_time_p95` above 250 ms.
- Spike in HTTP 500/503 rate correlated with `db_pool_acquire_timeout_total`.
- Alert on idle-in-transaction sessions older than 60 seconds.

## Root Causes
- Connection leak in application code paths that fail to close sessions after exceptions.
- Sudden traffic increase that exceeds pool sizing assumptions.
- Long-running queries holding connections for extended durations.
- Misconfigured worker concurrency creating more clients than the database can support.
- Stuck migrations, maintenance jobs, or ad hoc analyst queries consuming reserved capacity.

## Investigation Steps
1. Confirm customer impact by reviewing API error rate, latency, and saturation dashboards.
2. Check application pool metrics for active, idle, waiting, and timeout counters.
3. Query `pg_stat_activity` to identify idle, idle-in-transaction, blocked, and long-running sessions.
4. Compare current connection count against `max_connections` and reserved admin slots.
5. Identify the top callers by service, pod, user, and query fingerprint.
6. Review recent deploys, autoscaling events, migration runs, and batch workloads.
7. Inspect whether a single tenant, endpoint, or worker queue is driving abnormal demand.

## Remediation Steps
1. Throttle or temporarily disable non-critical jobs, report generation, and backfill workers.
2. Restart or scale down the offending service if a connection leak is isolated to a recent deployment.
3. Terminate clearly abandoned or idle-in-transaction sessions after validating they are safe to remove.
4. Increase application-side pool timeout and reduce concurrency to prevent cascading failures.
5. If headroom exists on the database host, apply a controlled increase to `max_connections` only as a temporary mitigation.
6. Roll back the latest release if the issue aligns with a code change that altered session handling.
7. Monitor recovery until pool wait time, error rate, and session count return to baseline.

## Prevention Measures
- Enforce connection lifecycle management with framework-level session wrappers.
- Add alerts on pool wait time, idle-in-transaction age, and pool exhaustion leading indicators.
- Load test connection usage under peak traffic and worker concurrency.
- Set sane pool limits per service so aggregate demand cannot exceed database capacity.
- Move heavy read workloads to replicas or caching layers where appropriate.
- Add automated linting or integration tests for leaked session patterns.
