# VPC Network Topology Template

```text
VPC: {{project_name}} ({{vpc_id}})
CIDR: {{vpc_cidr}}
|- Subnet: {{subnet_name_1}} ({{subnet_cidr_1}}) ~ {{az_1}}
|  |- {{resource_name}}: {{ip_or_endpoint}}
|  \- (empty)
|- Subnet: {{subnet_name_2}} ({{subnet_cidr_2}}) ~ {{az_2}}
|  |- {{resource_name}}: {{ip_or_endpoint}}
|  \- {{resource_name}}: {{ip_or_endpoint}}
\- Subnet: {{subnet_name_3}} ({{subnet_cidr_3}}) ~ {{az_3}}
   \- (empty)
```

> This template is used for generating the ASCII tree view. Variables are substituted by `topo-render.py`.
