# Database Recovery Playbook

## Symptoms
- Primary database is unavailable, degraded, or serving corrupt/incomplete results.
- Critical write paths such as checkout, order placement, or account changes are failing.
- Replication lag or standby promotion issues prevent normal failover.
- Application teams request immediate recovery guidance during a high-severity incident.

## Detection Signals
- Database health checks fail from multiple services and network locations.
- Error budgets are consumed rapidly for write-heavy customer journeys.
- Replica lag, WAL apply delay, or failover controller alarms breach thresholds.
- Storage, CPU, or memory metrics indicate the primary cannot recover without intervention.
- Backup validation or restore checks show recent failures that may affect recovery choices.

## Root Causes
- Hardware or cloud infrastructure failure affecting the primary node.
- Storage corruption, filesystem failure, or unavailable volumes.
- Operator error during migration, maintenance, or parameter changes.
- Runaway load leading to saturation and unresponsiveness.
- Replication breakage leaving no healthy promotion candidate.

## Investigation Steps
1. Establish incident commander, communications channel, and recovery objective priorities.
2. Determine whether the fastest safe path is failover, restart, point-in-time restore, or read-only degraded mode.
3. Validate the health and freshness of replicas, standbys, and backups.
4. Confirm replication lag, last successful WAL archive, and backup integrity status.
5. Identify any in-flight schema changes, long-running jobs, or maintenance actions.
6. Assess application tolerance for read-only mode, stale reads, or temporary feature disablement.
7. Capture timeline evidence and administrative decisions as recovery progresses.

## Remediation Steps
1. Freeze non-essential database changes, migrations, and analyst access.
2. Promote the healthiest replica if RPO and consistency checks are acceptable.
3. Repoint applications, connection strings, and proxies to the new primary.
4. If no viable replica exists, restore from the latest good backup and apply WAL up to the safe recovery point.
5. Bring services back in dependency order, prioritizing authentication, checkout, and order processing.
6. Monitor replication, lock contention, error rate, and data consistency validation queries.
7. Rebuild redundancy by provisioning new replicas immediately after primary service is stable.

## Prevention Measures
- Test failover and restore procedures on a fixed schedule with measured RTO/RPO.
- Maintain continuous backup validation and periodic point-in-time restore drills.
- Keep database topology, connection routing, and dependency maps current.
- Gate risky schema and infrastructure changes with rollback plans.
- Ensure applications can tolerate brief read-only or degraded operation modes.
- Track replica freshness and alert before promotion candidates become unusable.
