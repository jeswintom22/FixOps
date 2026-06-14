# Network Latency Incident

## Symptoms
- Cross-service calls exceed timeout budgets and trigger retries.
- Users experience slow page loads, delayed writes, or intermittent failures across multiple features.
- Replication, queue acknowledgment, or external API calls lag behind normal baselines.
- Service health may appear partially degraded without a single obvious failing component.

## Detection Signals
- TCP retransmits, packet loss, or connection establishment time increase above baseline.
- Inter-service latency percentiles rise across multiple unrelated applications.
- Synthetic probes fail regionally or from a subset of availability zones.
- Load balancer metrics show increased backend response time without corresponding CPU saturation.
- Traceroute or flow logs indicate a specific hop, subnet, or egress path under stress.

## Root Causes
- Network congestion, packet loss, or degraded link between zones or regions.
- Misconfigured routing, firewall, MTU, or service mesh policy.
- Load balancer or NAT gateway saturation.
- DNS latency or resolver instability causing delayed connections.
- Noisy-neighbor or cloud provider network impairment.

## Investigation Steps
1. Scope the incident by region, zone, subnet, cluster, and dependency path.
2. Compare application latency with infrastructure network metrics to separate compute from transport issues.
3. Review recent changes to network policies, security groups, routing, mesh config, and load balancers.
4. Run latency and packet loss checks from affected nodes or pods to key dependencies.
5. Inspect DNS resolution time, TLS handshake duration, and connection reuse behavior.
6. Use flow logs, traceroutes, or provider telemetry to isolate the degraded segment.
7. Confirm whether retries are compounding the issue and inflating traffic.

## Remediation Steps
1. Shift traffic away from the impaired zone, subnet, or region if capacity exists elsewhere.
2. Revert recent network configuration changes that align with incident onset.
3. Drain or replace overloaded load balancers, proxies, or NAT gateways.
4. Reduce timeout-sensitive background traffic to preserve headroom for customer-critical flows.
5. Increase client-side timeouts slightly if the underlying path is slow but functioning.
6. Engage the cloud provider or network team with timestamps, affected paths, and packet loss evidence.
7. Validate end-to-end recovery with synthetic checks and service latency dashboards.

## Prevention Measures
- Maintain multi-zone and multi-path resilience for critical dependencies.
- Monitor packet loss, retransmits, DNS latency, and connection setup time continuously.
- Review and test network policy changes with staged rollouts.
- Keep retry budgets bounded so degraded links are not overwhelmed further.
- Capacity-plan shared network components such as ingress, egress, and NAT layers.
- Run regular game days for zonal network impairment scenarios.
