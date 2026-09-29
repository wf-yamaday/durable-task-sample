# Azure infrastructure

`main.bicep` deploys the resources required to run this sample on Azure:

- Log Analytics workspace and Container Apps environment
- Virtual network, Container Apps infrastructure subnet, and private endpoint subnet
- Azure Container Registry
- Durable Task Scheduler and its task hub
- Durable Task Scheduler private endpoint and Private DNS zone
- A user-assigned managed identity for each workload
- Durable Task RBAC assignments scoped to the task hub
- Orchestrator and activity worker Container Apps
- An hourly client Container Apps Job (configurable with a UTC cron expression)

Both workers use the `azure-durabletask-scheduler` scaler and can scale to zero. The orchestrator worker reacts to `Orchestration` work items and the activity worker reacts to `Activity` work items.

## Azure Monitor dashboard with Grafana

The template creates `dash-<workload>-<environment>`, an Azure Monitor **Dashboard with Grafana** resource. It has no Azure Managed Grafana workspace or additional Grafana charge, and uses the signed-in user's Azure Monitor access.

The dashboard includes Container Apps replica counts and Durable Task Scheduler connected-worker, pending/active work-item, and action metrics. Open it from **Azure Monitor** > **Dashboards with Grafana** in the Azure portal. Dashboard viewers need `Reader` on the dashboard and `Monitoring Reader` on the monitored resources.

## Network topology

The template creates `vnet-<workload>-<environment>` with two subnets and `pep-dts-<workload>-<environment>` for the Scheduler private endpoint:

- `snet-cae-...` (`10.0.0.0/24`): delegated to `Microsoft.App/environments` for the Container Apps environment.
- `snet-pe-...` (`10.0.1.0/24`): hosts the Durable Task Scheduler private endpoint.

The scheduler uses the `scheduler` Private Link subresource. Its public network access is disabled, and `privatelink.durabletask.io` is linked to the virtual network so the normal Scheduler endpoint resolves to the private IP from Container Apps.

For development-only Dashboard access outside the VNet, explicitly enable public access and restrict it to the operator's public IP:

```sh
AZURE_RESOURCE_GROUP=<resource-group> \
mise run infra:deploy -- \
  schedulerPublicNetworkAccess=Enabled \
  schedulerIpAllowlist='["<public-ip>/32"]'
```

Keep public access disabled in production and access the dashboard through a private network path such as VPN or ExpressRoute.

## Deploy

### Naming convention

All resources in this sample target Japan East, so resource-group scoped resources follow the abbreviated form `<type>-<workload>-<environment>`. For example, the default parameters produce `ca-orchestrator-durabletask-dev`.

| Resource | Prefix | Example |
| --- | --- | --- |
| Container Apps environment | `cae` | `cae-durabletask-dev` |
| Container App | `ca` | `ca-orchestrator-durabletask-dev` |
| Container Apps Job | `job` | `job-client-durabletask-dev` |
| Durable Task Scheduler | `dts` | `dts-durabletask-dev` |
| Task Hub | `th` | `th-durabletask-dev` |
| Log Analytics workspace | `log` | `log-durabletask-dev` |
| User-assigned managed identity | `id` | `id-activity-durabletask-dev` |
| Azure Container Registry | `cr` | `crdurabletaskdevabc123` |

ACR names cannot contain hyphens and must be globally unique, so its name removes separators and appends a deterministic six-character suffix.

Set `workloadName` and `environmentName` in `main.bicepparam` to comply with your organization’s naming policy. The resource group is intentionally not created by this template; use the corresponding `rg-<workload>-<environment>` convention when creating it.

Sign in to Azure, select the target subscription, and create the resource group plus required resource-provider registrations:

```sh
mise install
az login
az account set --subscription <subscription-id>

AZURE_RESOURCE_GROUP=rg-<workload>-<environment> \
mise run infra:setup
```

First provision the shared resources and registry without the apps:

```sh
AZURE_RESOURCE_GROUP=<resource-group> \
mise run infra:what-if -- \
  workloadName=<workload> \
  environmentName=<environment> \
  deployApps=false

AZURE_RESOURCE_GROUP=<resource-group> \
mise run infra:deploy -- \
  workloadName=<workload> \
  environmentName=<environment> \
  deployApps=false
```

Push the three images to the returned registry login server. `IMAGE_TAG` defaults to `latest` and must match the image-tag parameters used for the final deployment.

```sh
AZURE_CONTAINER_REGISTRY_LOGIN_SERVER=<acr-login-server> \
mise run image:push
```

Then run the same deployment with the same naming parameters but without `deployApps=false` to create the Container Apps and Job.

```sh
AZURE_RESOURCE_GROUP=<resource-group> \
mise run infra:deploy -- \
  workloadName=<workload> \
  environmentName=<environment>
```

The client Job runs at `0 * * * *` (the start of every hour, UTC) by default. To use another schedule, pass a five-field UTC cron expression, for example:

```sh
AZURE_RESOURCE_GROUP=<resource-group> \
mise run infra:deploy -- \
  workloadName=<workload> \
  environmentName=<environment> \
  clientScheduleCronExpression='30 * * * *'
```

The deployment principal must be able to create role assignments, such as with the `Owner` or `User Access Administrator` role.
