# Service Scaling Playbook

## Symptoms
- Sustained demand growth pushes latency, queue depth, or CPU toward alert thresholds.
- Services remain healthy only because on-call staff are manually increasing replicas.
- Downstream dependencies begin to saturate as the service scales unevenly.
- Business events or launches require planned capacity expansion.

## Detection Signals
- CPU, memory, or request concurrency stays above 70 to 80 percent for prolonged periods.
- Queue lag or request latency breaches warning thresholds before errors appear.
- Horizontal pod autoscaler remains at or near maximum replicas.
- Rate of 429, 503, or shed traffic begins to increase.
- Forecasts from traffic models or business stakeholders indicate upcoming load growth.

## Root Causes
- Organic traffic increase or planned business event.
- Insufficient baseline capacity or conservative autoscaling policy.
- Resource imbalance where a stateless tier scales faster than its dependencies.
- Slow warm-up behavior preventing rapid automatic scale-out.
- Hidden single-threaded or shared-lock bottlenecks limiting effective horizontal scaling.

## Investigation Steps
1. Define the scaling objective: absorb current load, prepare for forecasted load, or restore SLO margin.
2. Identify the constraining resource for the service and each critical dependency.
3. Review current autoscaling settings, max replica caps, and cluster headroom.
4. Confirm whether startup time, cache warm-up, or connection pool settings will limit scaling efficiency.
5. Validate that downstream databases, caches, queues, and third-party APIs can absorb additional throughput.
6. Check recent deployment health to avoid scaling a broken version.
7. Align with business stakeholders on acceptable feature degradation if full scaling is not possible.

## Remediation Steps
1. Increase replicas or instance count in controlled increments while watching dependency saturation.
2. Adjust CPU or concurrency-based autoscaling targets to trigger earlier.
3. Pre-scale cluster nodes or capacity reservations before increasing workloads.
4. Tune connection pools, thread counts, and queue consumers so added replicas deliver real capacity.
5. Disable non-critical background processing if dependencies become the new bottleneck.
6. Apply rate limits or feature shedding if safe scaling headroom is exhausted.
7. Record the scaling breakpoints observed for future capacity models.

## Prevention Measures
- Maintain load forecasts tied to business calendars and launch planning.
- Regularly test autoscaling responsiveness under realistic warm-up and dependency conditions.
- Keep max replica limits, quotas, and cluster autoscaler settings aligned.
- Capacity-plan the full request path, not just the front-end service tier.
- Build dashboards showing marginal gain from each additional replica.
- Establish a pre-event checklist for major traffic windows.
