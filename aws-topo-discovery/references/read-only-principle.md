# READ-ONLY PRINCIPLE

The core design principle of this Skill is **Absolute Read-Only**. Before executing any operation, the Agent MUST enforce the following red lines:

| Rule | Description |
| **NO Write Operations** | Never execute any `Create`, `Update`, `Modify`, `Delete`, `Associate`, `Disassociate`, `Authorize`, `Revoke`, `Run`, `Terminate` operation |
| **NO State Changes** | Never alter the state of any cloud resource, including but not limited to instance start/stop, security group rule changes, EIP association, etc. |
| **NO Credential Exposure** | Never output full AK/Secret; output must be masked as `AKIA******SECRET` or `***` |
| **Read-Only API Only** | Only invoke `Describe*`, `List*`, `Get*` APIs (see [Safety Gate](references/safety-gate.md)) |

**Violation of this principle = critical security breach. HALT immediately and report to the user.**
