# Agent Architecture

## Log Agent

Responsibilities:

- Analyze logs
- Explain anomalies
- Extract findings

Inputs:

- Logs
- Detection metadata

Outputs:

- Findings

---

## Metric Agent

Responsibilities:

- Analyze metrics
- Identify abnormal behavior

Inputs:

- Metrics

Outputs:

- Metric findings

---

## Knowledge Agent

Responsibilities:

- Search previous incidents
- Retrieve runbooks
- Retrieve known fixes

Inputs:

- Incident memory

Outputs:

- Similar incidents
- Suggested fixes

---

## Correlation Agent

Responsibilities:

- Analyze dependencies
- Build causal chains

Inputs:

- Logs
- Metrics
- Deployments

Outputs:

- Correlation findings

---

## Remediation Agent

Responsibilities:

- Evaluate possible fixes

Outputs:

- Ranked remediation options

---

## Coordinator Agent

Responsibilities:

- Combine all agent outputs
- Resolve conflicts
- Produce final investigation

Only the coordinator can generate final recommendations.