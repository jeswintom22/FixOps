# Traffic Spike Playbook

## Symptoms
- Customer demand increases sharply over minutes rather than following normal diurnal patterns.
- Latency and partial errors begin appearing across customer-facing endpoints.
- Autoscaling activates but may lag behind the load ramp.
- Downstream services, caches, or databases show secondary saturation.

## Detection Signals
- Requests per second exceed forecast or historical peak thresholds.
- Load balancer concurrency, queue depth, and p95 latency rise together.
- Traffic source analysis shows concentration from a campaign, crawler, or abusive actor.
- CDN cache miss rate, origin fetch rate, or WAF events change materially.
- Synthetic checks remain healthy initially while real-user performance degrades under scale.

## Root Causes
- Planned marketing launch or product announcement.
- Unplanned virality or external event driving user demand.
- Bot traffic, scraper activity, or low-grade DDoS behavior.
- Retry storm from a degraded dependency causing amplified inbound traffic.
- Cache invalidation or CDN bypass event sending excess traffic to origin.

## Investigation Steps
1. Establish whether the spike is legitimate demand, accidental amplification, or hostile traffic.
2. Break down traffic by geography, client type, route, tenant, and authentication status.
3. Compare current shape to previous peak events and forecast assumptions.
4. Check CDN, WAF, load balancer, and origin dashboards for where pressure is accumulating.
5. Inspect autoscaling lag, instance warm-up time, and dependency health.
6. Determine whether one feature or endpoint can be degraded without harming core transactions.
7. Coordinate business communications if customer-visible throttling is likely.

## Remediation Steps
1. Scale edge, application, and queue-processing tiers in priority order.
2. Increase cache TTLs or enable cache-friendly behavior where correctness permits.
3. Activate WAF rules, bot filtering, or rate limits for abusive patterns.
4. Shed non-critical traffic such as recommendations, exports, and background sync.
5. Protect write paths by prioritizing checkout, auth, and order confirmation traffic classes.
6. Reduce retry aggressiveness and circuit-break failing dependencies to prevent amplification.
7. Continue until demand stabilizes and service health recovers with adequate margin.

## Prevention Measures
- Rehearse event capacity plans using historical and worst-case traffic models.
- Keep feature flags for expensive optional functionality.
- Maintain clear traffic classification and priority policies.
- Use CDN and caching strategies that can absorb origin surges.
- Build dashboards that separate real-user demand from automated traffic.
- Review every major spike for missed signals and scaling delays.
