# Memory Leak Investigation

## Symptoms
- Resident memory grows steadily over hours or days and does not return after traffic normalizes.
- Pods are evicted or restarted with OOMKilled events.
- Garbage collection time increases, reducing throughput and increasing tail latency.
- Node memory pressure affects colocated services and can trigger wider instability.

## Detection Signals
- Container working set or process RSS shows monotonic growth across deploy cycles.
- OOM kill count increases for a single workload or version.
- Heap usage after full GC remains above the normal watermark.
- Swap activity or page fault rate increases on stateful hosts.
- Memory growth aligns with specific endpoints, message types, or tenant activity.

## Root Causes
- Application objects retained due to unbounded caches, references, or listener leaks.
- High-cardinality in-memory data structures from malformed traffic or batch jobs.
- Native library leaks outside the managed heap.
- Large response buffering, file handling, or image/document processing paths.
- Misconfigured cache TTLs or disabled eviction logic.

## Investigation Steps
1. Confirm the pattern across versions, replicas, and environments to distinguish leak from legitimate load growth.
2. Review memory dashboards for RSS, heap, GC pause, allocation rate, and restart count.
3. Correlate leak onset with deploys, feature flags, and workload mix changes.
4. Capture heap dumps, allocation profiles, or language-specific memory snapshots during growth.
5. Compare the largest retained object classes or buffers between healthy and unhealthy replicas.
6. Inspect application logs for repeated warnings around cache growth, retries, or failed cleanup paths.
7. Verify whether sidecars, agents, or native extensions are responsible rather than the main process.

## Remediation Steps
1. Roll back the suspected release or disable the implicated feature flag.
2. Restart affected pods in a controlled manner to recover capacity while investigation continues.
3. Reduce traffic to the expensive endpoint or tenant that accelerates memory growth.
4. Lower cache sizes, restore TTLs, or disable in-memory batching where safe.
5. Increase memory limits only as a short-term containment measure with close monitoring.
6. Remove stuck work items or malformed payloads that trigger pathological allocation behavior.
7. Preserve diagnostic artifacts before recycling the final unhealthy replica.

## Prevention Measures
- Add per-service memory SLOs and alerts on growth slope, not just absolute usage.
- Include heap profiling and leak tests in pre-production validation for critical services.
- Bound caches, queues, and batch sizes by configuration.
- Track dependency and native library upgrades that can affect memory behavior.
- Use canaries with memory regression gates before full rollout.
- Document standard dump capture procedures for each runtime.
