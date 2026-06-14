# Database Pool Exhaustion Incident

## Symptoms
- Core APIs serving checkout, account updates, and order history returned intermittent 500s.
- Pods remained healthy at the Kubernetes layer but request handlers stalled waiting for database connections.
- Background jobs accumulated and SLA-bound workflows such as refund processing were delayed.
- On-call responders observed sharp increases in customer-facing latency before hard failures.

## Detection Signals
- Application pool utilization pinned at 100 percent for 17 minutes.
- `db_pool_acquire_timeout_total` increased from a baseline of 0 to 2,900 events per minute.
- Postgres `numbackends` reached 97 percent of `max_connections`.
- `pg_stat_activity` showed hundreds of idle-in-transaction sessions from the order-service deployment.
- Error rate increased immediately after rollout of version `2026.06.12.4`.

## Root Causes
- A regression in the order-service transaction wrapper failed to close sessions on exception paths.
- Increased refund traffic after a partner import job created a larger-than-normal volume of failing transactions.
- Worker concurrency settings allowed the leaking code path to consume the pool rapidly across replicas.

## Investigation Steps
1. Confirmed the incident window aligned with the rollout of the new order-service version.
2. Queried `pg_stat_activity` and identified a large concentration of stale sessions tied to the same application user.
3. Compared pool metrics by service and found order-service driving nearly all connection wait time.
4. Reviewed the code diff and isolated a missing `finally` cleanup path in the transaction helper.
5. Verified no infrastructure-level database saturation existed beyond connection exhaustion.

## Remediation Steps
1. Rolled back order-service to the last known good release.
2. Terminated abandoned idle-in-transaction sessions after confirming they were not attached to active writes.
3. Reduced worker concurrency temporarily to slow pool consumption during recovery.
4. Monitored latency and pool wait metrics until they returned to normal operating range.
5. Paused the partner refund import job until the fix was validated.

## Prevention Measures
- Add integration tests that simulate exceptions and assert session cleanup.
- Alert on idle-in-transaction age and connection wait time before full exhaustion occurs.
- Set stricter per-service pool caps so one deployment cannot consume nearly all database connections.
- Require canary analysis on connection lifecycle metrics for services using shared database clusters.
- Review worker concurrency changes alongside database capacity assumptions.
