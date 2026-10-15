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
- A manually triggered client Container Apps Job (no automatic schedule)
- Microsoft Foundry resource (`AIServices`) with a `gpt-5.6-luna` deployment
- Blob Storage with private `input` and `results` containers
- Activity identity: Cognitive Services OpenAI User, input Blob Data Reader, results Blob Data Contributor

Both workers use the `azure-durabletask-scheduler` scaler and can scale to zero. The orchestrator worker reacts to `Orchestration` work items and the activity worker reacts to `Activity` work items.

## Azure Monitor dashboard with Grafana

The template creates `dash-<workload>-<environment>`, an Azure Monitor **Dashboard with Grafana** resource. It has no Azure Managed Grafana workspace or additional Grafana charge, and uses the signed-in user's Azure Monitor access.

The dashboard includes Container Apps replica counts and Durable Task Scheduler connected-worker, pending/active work-item, and action metrics. Open it from **Azure Monitor** > **Dashboards with Grafana** in the Azure portal. Dashboard viewers need `Reader` on the dashboard and `Monitoring Reader` on the monitored resources.

## Network topology

The template creates `vnet-<workload>-<environment>` with two subnets and `pep-dts-<workload>-<environment>` for the Scheduler private endpoint:

- `snet-cae-...` (`10.0.0.0/24`): delegated to `Microsoft.App/environments` for the Container Apps environment.
- `snet-pe-...` (`10.0.1.0/24`): hosts the Durable Task Scheduler private endpoint.

The scheduler uses the `scheduler` Private Link subresource. Its public network access is disabled, and `privatelink.durabletask.io` is linked to the virtual network so the normal Scheduler endpoint resolves to the private IP from Container Apps.

The Container Apps environment uses `vnetConfiguration.internal: true` and `publicNetworkAccess: Disabled`. This removes public application ingress; it does not disable outbound internet access. Workers access Foundry and Blob through private endpoints and continue using Managed Identity authentication. The client Job remains manually triggered through Azure Resource Manager. Switching an existing external environment to internal requires deleting its apps and Jobs, deleting the environment, and redeploying; changing the Bicep property alone cannot update the existing environment in place. Preserve Foundry, Blob, DTS, identities, and the VNet during that replacement.

Foundry (`account`) and Storage (`blob`) private endpoints use the existing `snet-pe-...` subnet. Private DNS zones `privatelink.openai.azure.com`, `privatelink.cognitiveservices.azure.com`, `privatelink.services.ai.azure.com`, and `privatelink.blob.core.windows.net` are linked to the workload VNet. Applications retain their normal service URLs; DNS resolves those names to private IPs inside the VNet. Both services have public network access disabled. Local data upload/download and the Foundry playground require VNet connectivity (for example VPN or a host in the VNet) and appropriate DNS/RBAC. ARM resource management remains available from outside the VNet. ACR, authentication, and monitoring are not made private by this change, so this is not an entirely internet-isolated environment.

`scripts/private_network_smoke.py` is a dev-specific test intended to be passed as a one-off `python -u -c` command override to the existing client Job image, not run on the local machine. It checks that all three Foundry hostnames and the Blob hostname resolve to `10.0.1.0/24`, starts exactly one ten-row/two-parallel orchestration, waits for completion, and fails unless all ten reviews succeed. It logs the instance ID and the final output (including the result Blob path and metrics), so verification does not require opening Blob's public endpoint. The script's hostnames and expected subnet are specific to this repository's dev deployment. Do not persist this command override in the normal Job template.

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

The client Job uses a `Manual` trigger to avoid unintended repeated model charges. Start it explicitly after uploading the input CSV:

```sh
az containerapp job start \
  --resource-group <resource-group> \
  --name <client-job-name>
```

Existing scheduled Jobs remain scheduled until this template is redeployed. Changing the trigger does not stop an already-started orchestration. The previous `clientScheduleCronExpression` parameter has been removed.

The deployment principal must be able to create role assignments, such as with the `Owner` or `User Access Administrator` role.

## Continuous image deployment

Each `build-*.yaml` GitHub Actions workflow runs when its corresponding workload is merged into `main`. It pushes both the commit-SHA tag and `latest` to the dev ACR, then updates the corresponding Container App or Job template. Worker updates create a new revision, while the client Job template is updated so its next manual execution uses `latest`. Image deployment alone does not change an existing Job's trigger; redeploy Bicep to apply the Manual trigger.

Configure GitHub Actions OpenID Connect authentication before merging. Create a federated credential for the `main` branch of `wf-yamaday/durable-task-sample`, assign the identity `AcrPush` on `crdurabletaskdev5iwykh` and `Contributor` on `rg-durabletask-dev`, and add these GitHub repository variables:

- `AZURE_CLIENT_ID`
- `AZURE_TENANT_ID`
- `AZURE_SUBSCRIPTION_ID`

## Review data and model

The default model is `gpt-5.6-luna`, version `2026-07-09` from the [official model catalog](https://ai.azure.com/catalog/models/gpt-5.6-luna), `GlobalStandard`, capacity `10`. Availability and quota depend on your subscription and region; Bicep compilation does not validate these. Override `openAiLocation`, `openAiModelName`, `openAiModelVersion`, `openAiDeploymentSku`, or `openAiDeploymentCapacity` as needed. The model must support structured outputs and v1 Chat Completions. GlobalStandard processing is not guaranteed to stay in Japan.

Foundry and Storage use Private Link with public network access disabled; anonymous Blob access and shared-key/local-key authentication are also disabled. Run the data-plane commands below from a VNet-connected host with private DNS resolution. Review text and analysis also appear in DTS history.

If model quota is not yet available, provision the Foundry account, Blob Storage, containers, and RBAC first without creating the model:

```sh
AZURE_RESOURCE_GROUP=<resource-group> \
mise run infra:deploy -- deployOpenAiModel=false
```

This leaves the configured model deployment name in the worker settings, but inference cannot run until the model is deployed. Do not start the client Job yet. Once quota is available, redeploy with `deployOpenAiModel=true`. Setting false skips model creation; it does not delete an existing model in an incremental deployment.

### Microsoft Foundry resource

While the GPT-5.6-luna quota request is pending, `main.bicepparam` selects `gpt-5-mini` version `2025-08-07` with reasoning effort `low` and a 4,096-token completion budget (including reasoning). The base template defaults remain GPT-5.6-luna. The worker settings are supplied through environment variables, so this switch does not require a new application image. To return to Luna, update the parameter file's model name/version, reasoning effort (`none`), and completion budget (`1024`).

The account uses `kind: AIServices`, `allowProjectManagement: true`, and a system-assigned managed identity. Existing OpenAI accounts are upgraded in place following the [official migration guidance](https://learn.microsoft.com/en-us/azure/foundry/how-to/upgrade-azure-openai). The existing `aoai-...` resource name, custom subdomain, OpenAI endpoint, and inference RBAC are retained; no account replacement or Blob migration is needed.

The worker continues using the OpenAI v1 API and its user-assigned identity. The `openAi...` Bicep parameters/outputs and `AZURE_OPENAI_...` settings are retained for compatibility. This template does not create a Foundry Project or deploy agents; the Foundry account is enabled for project management so those can be added separately. Changing the resource kind does not increase model quota.

1. Provision with `deployApps=false` as above. This creates the model, storage, and `input`/`results` containers too.
2. Download [Amazon Fine Food Reviews](https://www.kaggle.com/datasets/snap/amazon-fine-food-reviews) and extract `Reviews.csv`. Check its license before use. Optionally use Kaggle CLI:

   ```sh
   kaggle datasets download -d snap/amazon-fine-food-reviews --unzip -p ./data
   ```

3. Assign the uploading user `Storage Blob Data Contributor` on the storage account (management-plane Contributor alone is insufficient). The local activity worker user additionally needs `Cognitive Services OpenAI User` on the OpenAI account. Allow time for role propagation.

   For a small smoke test, prepare ten reviews (two per rating) with only `Id`, `Text`, and `Score`. The script reads the archive without extracting the full dataset and refuses to overwrite the output file:

   ```sh
   mise --cd activity-worker exec -- uv run python ../scripts/prepare_reviews.py \
     <path-to-amazon-fine-food-reviews.zip> ../data/reviews-smoke.csv
   ```

   Upload this file as `input/reviews-smoke.csv` instead of the full dataset, then explicitly select it for a single manual execution:

   ```sh
   az containerapp job start \
     --resource-group <resource-group> \
     --name <client-job-name> \
     --container-name client \
     --command durable-task-client \
     --args 10 --parallelism 2 --container input --blob reviews-smoke.csv
   ```

   This overrides only that execution, not the Job schedule or persistent template. The balanced sample is for smoke testing, not representative accuracy measurement.
4. Upload using the `storageAccountName` deployment output:

   ```sh
   az storage blob upload \
     --auth-mode login \
     --account-name <storage-account-name> \
     --container-name input \
     --name Reviews.csv \
     --file ./data/Reviews.csv \
     --overwrite
   ```

5. Push the images, then deploy the apps. The Job does not run automatically. Each manual start processes up to the first 100 rows with parallelism 5 and incurs model usage charges. Start it with `az containerapp job start --resource-group <resource-group> --name <client-job-name>`.

Download a completed report:

```sh
az storage blob download \
  --auth-mode login \
  --account-name <storage-account-name> \
  --container-name results \
  --name <instance-id>/results.json \
  --file ./results.json
```
