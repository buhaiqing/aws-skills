# Relationship with Existing Skills

| Relationship | Description |
| **Does Not Replace** | This Skill does not replace any product-level Skill (e.g., `aws-ec2-ops`, `aws-vpc-ops`) |
| **Composable Calls** | This Skill aggregates cross-product topology by calling read-only APIs of each product |
| **Discovery vs Operations** | This Skill handles "discovery"; product Skills handle "operations" — guide users to the corresponding product Skill for resource changes |
| **AIOps Integration** | `aws-aiops-cruise` invokes `topo-scan.sh` via `cruise-topo-render.py`; health overlay from `cruise-*.json` |
