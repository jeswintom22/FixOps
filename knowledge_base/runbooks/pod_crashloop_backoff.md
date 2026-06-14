# Pod CrashLoopBackOff

## Symptoms
- Kubernetes workloads continuously restart and never remain ready long enough to serve traffic.
- Deployments show unavailable replicas and degraded capacity.
- Logs may show startup exceptions, missing config, failed migrations, or probe failures.
- Related services experience increased latency or error rate due to reduced replica count.

## Detection Signals
- Alert on `CrashLoopBackOff` state, restart count, or unavailable replica percentage.
- Readiness and liveness probe failures spike after a deploy or config change.
- Events show image pull, secret mount, or volume attach issues preceding restarts.
- Pod termination reasons include `Error`, `OOMKilled`, or non-zero exit codes.
- HPA or rollout controller stalls because healthy replicas never come online.

## Root Causes
- Invalid environment variable, secret, or configuration pushed during deployment.
- Application startup regression, schema mismatch, or missing dependency.
- Liveness probe too aggressive for cold start behavior.
- Memory or CPU constraints causing process termination during initialization.
- External dependency failure causing the app to exit instead of retrying.

## Investigation Steps
1. Describe the pod and review restart reasons, recent events, and probe outcomes.
2. Pull logs from the current and previous container instances.
3. Compare the failing pod spec with the last known healthy revision.
4. Validate secrets, config maps, mounted files, and startup command arguments.
5. Check whether dependency endpoints such as databases, queues, or third-party APIs are reachable.
6. Inspect resource requests, limits, and node pressure conditions.
7. Confirm whether only new pods fail or existing pods are also recycling.

## Remediation Steps
1. Roll back the deployment if the issue started immediately after a release.
2. Fix or restore the broken secret, config map, image tag, or startup command.
3. Relax liveness/readiness probe thresholds temporarily if startup is slower but healthy.
4. Increase memory or CPU requests if startup resource starvation is evident.
5. Disable startup-time hard dependencies or enable retry loops where supported.
6. Cordon and drain a problematic node if failures are localized to host conditions.
7. Verify recovery through stable readiness, restart count flattening, and restored error budgets.

## Prevention Measures
- Use progressive delivery and canary analysis for config and image changes.
- Validate secrets and startup configuration before deployment.
- Separate startup, readiness, and liveness concerns in probe design.
- Ensure applications fail gracefully on transient dependency issues.
- Keep rollback procedures and previous stable image references readily available.
- Track restart trends and probe flakiness as first-class reliability signals.
