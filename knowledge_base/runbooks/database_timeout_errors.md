# Database Timeout Errors

## Symptoms
- Users report intermittent slow pages, failed checkouts, or blank dashboards.
- Services emit query timeout, transaction timeout, or statement cancellation errors.
- Request latency climbs before hard failures appear, often with thread pool saturation.
- Scheduled jobs begin missing SLAs and queue depth increases.

## Detection Signals
- Increase in `db_query_timeout_total` or ORM timeout exceptions.
- Query latency percentiles exceed service SLO thresholds.
- Postgres metrics show lock wait time, I/O saturation, or replication lag increases.
- Application retries rise sharply for read and write operations.
- Infrastructure dashboards show elevated disk latency or CPU steal on the database node.

## Root Causes
- Regressed query plans after schema changes, data skew, or stale statistics.
- Lock contention between transactional workloads and maintenance jobs.
- Storage latency spikes causing normal queries to exceed timeout thresholds.
- Timeouts configured too aggressively for high-cardinality or large-result queries.
- Dependency saturation upstream causing requests to hold transactions open too long.

## Investigation Steps
1. Determine whether the failures are reads, writes, or a specific transaction path.
2. Pull sample error logs with query names, tables, and calling services.
3. Review recent schema migrations, index changes, and `ANALYZE` or vacuum health.
4. Check slow query logs, `pg_stat_statements`, and blocked query chains.
5. Inspect host-level CPU, memory, disk queue, and network metrics for the database tier.
6. Validate whether retries or client timeouts are amplifying load.
7. Compare current behavior to the last known healthy baseline.

## Remediation Steps
1. Cancel or terminate the most expensive runaway queries after validating business impact.
2. Pause non-essential maintenance, analytics, and backfill workloads.
3. Add or restore the missing index if the regression is clearly understood and safe.
4. Reduce request concurrency or enable traffic shedding for the affected endpoints.
5. Tune timeout values upward temporarily if the database is healthy but slow due to transient load.
6. Fail over to a healthy replica or standby if the primary is resource-constrained or degraded.
7. Roll back the triggering application or schema change when timing strongly matches the incident.

## Prevention Measures
- Maintain query performance baselines and regression detection in CI and staging.
- Keep table statistics current and monitor bloat, vacuum lag, and index effectiveness.
- Separate OLTP and analytical workloads to reduce lock and I/O contention.
- Use circuit breakers and bounded retries to avoid retry storms.
- Review timeout values per workload class rather than using one global default.
- Create alerts on lock waits, slow queries, and database storage latency.
