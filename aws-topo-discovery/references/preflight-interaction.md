# Pre-flight Interaction

Before running a scan, **MUST** confirm the following options with the user:

```
📋 Topology Scan Configuration:

1. Report mode (required):
   [1] Brief — VPC + Subnet + ELB/EIP + resource count summary (default)
   [2] Detailed — Brief + full attributes and inventory for all EC2/RDS/EKS/Lambda/Security Groups

2. Topology format:
   [1] ASCII tree — terminal-friendly, directly readable (default)
   [2] Mermaid diagram — flow/render support, suitable for embedding in docs
   [3] Both

3. Output structure:
   [1] Single file — all content written to report.md (default)
   [2] Multi-file — split into topology.md + inventory.md + summary.md

4. Project name/identifier (optional):
   [input]: Custom report title prefix (defaults to auto-extract from VPC name)

5. Health overlay (optional, integrates with `aws-aiops-orchestrator`):
   [input]: Inspection JSON report path (automatically overlays health status onto topology)

Reply with option numbers or descriptions to confirm before scanning begins.
```
