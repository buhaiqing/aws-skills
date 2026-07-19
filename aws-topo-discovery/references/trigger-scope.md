# Trigger & Scope

## SHOULD Use When

- User needs to view/scan/discover/audit AWS network topology
- User needs a resource inventory or asset list under a VPC
- User needs to know which VPCs/EIPs/ELBs/EC2 instances exist in the account
- User needs a network architecture diagram or resource report
- User needs to export cloud resources as Terraform HCL (`export-hcl`)
- User needs to create an infrastructure baseline snapshot (`baseline`)
- User needs to compare configuration changes between two baselines (`baseline-diff`)
- User needs cross-account resource scanning (via `--assume-role`)
- Keywords: network topology, VPC structure, resource inventory, cloud resource scan, Terraform HCL export, infrastructure baseline
- User says "scan the network", "show me what resources exist", "generate a topology map", "export HCL", "create a baseline"

## SHOULD NOT Use When

- User needs to create/modify/delete resources → delegate to the corresponding product Skill
- User needs to troubleshoot resource failures or performance issues → delegate to monitoring/diagnostic Skills
- User needs billing/cost queries → no in-repo skill; use AWS Cost Explorer / Billing console directly
- User needs to configure security policies → delegate to `aws-iam-ops` / `aws-waf-ops`
- User needs to provision cloud resources via `terraform apply` → delegate to the Terraform workflow
