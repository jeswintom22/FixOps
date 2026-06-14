# CPU Spike Response

## Symptoms
- Services show rising request latency, timeouts, and autoscaling activity.
- Nodes report high load average and CPU throttling.
- Batch workloads take significantly longer or stop processing new items.
- Logging and metrics pipelines may lag as agents compete for CPU.

## Detection Signals
- CPU utilization above 85 percent for 10 minutes on critical workloads.
- Container throttling metrics increase on Kubernetes workloads with CPU limits.
- Request latency increases alongside saturation rather than erroring immediately.
- Top endpoint or job metrics show a single hot path dominating resource use.
- Deploy and autoscaling events coincide with the spike window.

## Root Causes
- Traffic surge or abusive client behavior.
- Inefficient code path introduced in a recent release.
- Runaway background job, retry storm, or unbounded loop.
- Garbage collection churn or excessive serialization/compression work.
- Noisy-neighbor effect on shared nodes or virtualized hosts.

## Investigation Steps
1. Identify whether the spike is service-wide, node-local, or isolated to a subset of pods.
2. Correlate the start time with deploys, cron jobs, cache misses, and traffic anomalies.
3. Review per-endpoint, per-queue, or per-tenant usage to find the hottest workload.
4. Inspect container throttling, garbage collection, and thread pool metrics.
5. Sample process stacks or profiles if the issue persists long enough for capture.
6. Validate whether downstream slowness is causing expensive retries or tight polling loops.
7. Check node placement for co-located workloads that may be contending for cores.

## Remediation Steps
1. Scale out the affected service if the spike is demand-driven and the dependency chain can absorb it.
2. Roll back the most recent release if profiling or timing implicates new code.
3. Disable or rate-limit the hottest background job, tenant, or endpoint.
4. Raise CPU requests temporarily or redistribute workloads to less-contended nodes.
5. Enable traffic shedding for non-critical features to protect core transactions.
6. Restart clearly wedged workers only after capturing enough evidence for follow-up analysis.
7. Continue observing latency, throttling, and queue depth until steady state returns.

## Prevention Measures
- Maintain CPU saturation alerts with endpoint and tenant breakdowns.
- Profile critical services regularly and track performance regressions in CI.
- Apply rate limits and backpressure to costly APIs and background jobs.
- Right-size CPU requests and limits to reduce throttling risk.
- Schedule heavy maintenance tasks away from peak traffic periods.
- Keep feature flags available to disable non-critical expensive paths quickly.
