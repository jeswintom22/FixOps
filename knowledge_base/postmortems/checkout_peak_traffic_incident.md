# Checkout Peak Traffic Incident

## Symptoms
- Checkout latency exceeded the customer SLO and cart completion rate dropped materially.
- A subset of customers saw 503 responses during payment authorization and order submission.
- Autoscaling increased frontend and API replicas, but database and queue latency continued to climb.
- Support volume increased due to duplicate clicks, delayed confirmation emails, and abandoned carts.

## Detection Signals
- Requests per second on `/checkout` reached 3.4x the prior seasonal peak.
- API p95 latency rose from 420 ms to 4.8 s between 18:07 and 18:19 UTC.
- Queue depth for order-processing workers exceeded 180,000 pending jobs.
- Database CPU remained below saturation, but connection wait time and lock contention increased sharply.
- CDN cache hit ratio fell after a misconfigured cache-bypass rule was deployed to a promotional landing flow.

## Root Causes
- A planned flash-sale campaign generated legitimate peak traffic beyond the tested envelope.
- A same-day CDN ruleset change bypassed origin caching for several checkout-adjacent APIs.
- Retry behavior in the checkout client amplified write traffic when responses slowed.
- Worker concurrency increased database pressure without improving order completion throughput.

## Investigation Steps
1. Reviewed edge, application, queue, and database telemetry to identify where latency first accumulated.
2. Compared live traffic against the event capacity plan and confirmed actual demand exceeded forecast by more than 2x.
3. Isolated the drop in CDN cache effectiveness to a ruleset deployed 11 minutes before the incident began.
4. Examined client telemetry and found aggressive retries on payment status polling.
5. Validated that the payment provider remained healthy and was not the primary bottleneck.

## Remediation Steps
1. Reverted the CDN cache-bypass rule and restored expected edge caching behavior.
2. Increased API and worker replicas while capping worker database concurrency to reduce pool pressure.
3. Disabled non-essential checkout recommendations and promotional widgets.
4. Tuned retry intervals for payment status polling through a feature flag.
5. Prioritized checkout and order-confirmation traffic over lower-value browsing traffic at the load balancer layer.

## Prevention Measures
- Expand event load testing to include edge-cache miss scenarios and client retry amplification.
- Require production validation for CDN rules that affect origin cacheability.
- Add explicit traffic class protection so checkout retains capacity during peak events.
- Review flash-sale forecasts jointly with engineering, marketing, and SRE one week before launch.
- Monitor cache hit ratio and checkout retries as first-tier pre-incident signals.
