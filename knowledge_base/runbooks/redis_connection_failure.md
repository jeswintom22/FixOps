# Redis Connection Failure

## Symptoms
- Cache-backed features return errors, stale data, or unexpectedly hit the primary database.
- Session creation or token validation fails if Redis is used as a state store.
- Worker queues stall when brokers or locks rely on Redis availability.
- Application logs show connection refused, timeout, TLS handshake, or authentication failures.

## Detection Signals
- Redis availability checks fail from one or more application subnets.
- Cache hit ratio drops sharply while database read traffic rises.
- `redis_connection_errors_total` and reconnect attempts increase.
- Sentinel or cluster dashboards show failover churn, node flapping, or slot unavailability.
- Host metrics indicate memory pressure, blocked clients, or network packet loss.

## Root Causes
- Redis instance outage, failover instability, or node replacement event.
- Security group, network policy, or firewall changes blocking client access.
- Expired credentials, rotated secrets, or mismatched TLS configuration.
- Memory exhaustion causing eviction storms or process termination.
- DNS resolution issues directing clients to a stale endpoint.

## Investigation Steps
1. Confirm whether the issue is global, zonal, or limited to a single service.
2. Test reachability from an affected pod or node to the Redis endpoint and port.
3. Review Redis logs for restart events, failover decisions, OOM conditions, and auth failures.
4. Check recent changes to secrets, certificates, service discovery, and network policies.
5. Inspect client metrics for timeout, reconnect, and pool saturation patterns.
6. Validate cluster health, replica lag, and slot ownership if using Redis Cluster.
7. Measure downstream impact on databases, job workers, and session-dependent flows.

## Remediation Steps
1. Restore connectivity by reverting the blocking network or secret change.
2. Fail over to a healthy Redis primary if the current leader is unresponsive.
3. Restart only the affected client deployments if they are pinned to stale DNS or broken pooled connections.
4. Reduce cache pressure by disabling non-critical cache warmers and bulk consumers.
5. Scale the Redis tier or free memory if the outage is caused by saturation.
6. Enable degraded mode in applications that can bypass cache for critical customer journeys.
7. Validate recovery by checking hit ratio, reconnect rate, and dependent service latency.

## Prevention Measures
- Use highly available Redis topologies with tested failover procedures.
- Monitor connection errors, memory fragmentation, evictions, and blocked clients.
- Automate secret rotation validation and TLS compatibility checks.
- Keep client timeouts, retries, and backoff conservative to avoid storm behavior.
- Document degraded-mode behavior for cache-optional services.
- Exercise regional and zonal failover drills regularly.
