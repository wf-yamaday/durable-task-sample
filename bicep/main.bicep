targetScope = 'resourceGroup'

@description('Azure region for all resources. This sample defaults to Japan East.')
param location string = 'japaneast'

@description('Lowercase alphanumeric workload or application name used in resource names.')
param workloadName string

@description('Deployment environment, such as dev, test, stage, or prod.')
param environmentName string

@description('Tag for the client image in the provisioned Azure Container Registry.')
param clientImageTag string = 'latest'

@description('Tag for the orchestrator worker image in the provisioned Azure Container Registry.')
param orchestratorWorkerImageTag string = 'latest'

@description('Tag for the activity worker image in the provisioned Azure Container Registry.')
param activityWorkerImageTag string = 'latest'

@description('UTC cron expression for starting the client Container Apps Job. The default runs at the start of every hour.')
param clientScheduleCronExpression string = '0 * * * *'

@description('Whether to deploy Container Apps and the client Job. Set false to provision the registry before its images are pushed.')
param deployApps bool = true

@description('CIDR ranges allowed to access Durable Task Scheduler over its public endpoint. Use /32 for an individual IPv4 address.')
param schedulerIpAllowlist array = []

@allowed([
  'Disabled'
  'Enabled'
])
@description('Whether Durable Task Scheduler accepts public endpoint connections. Keep Disabled unless dashboard access is required outside the VNet.')
param schedulerPublicNetworkAccess string = 'Disabled'

var resourceNameSuffix = '${workloadName}-${environmentName}'
var containerAppsEnvironmentName = 'cae-${resourceNameSuffix}'
var containerRegistryName = 'cr${workloadName}${environmentName}${substring(uniqueString(subscription().id, resourceGroup().id), 0, 6)}'
var schedulerName = 'dts-${resourceNameSuffix}'
var taskHubName = 'th-${resourceNameSuffix}'
var logAnalyticsWorkspaceName = 'log-${resourceNameSuffix}'
var clientIdentityName = 'id-client-${resourceNameSuffix}'
var orchestratorIdentityName = 'id-orchestrator-${resourceNameSuffix}'
var activityIdentityName = 'id-activity-${resourceNameSuffix}'
var virtualNetworkName = 'vnet-${resourceNameSuffix}'
var containerAppsInfrastructureSubnetName = 'snet-cae-${resourceNameSuffix}'
var privateEndpointSubnetName = 'snet-pe-${resourceNameSuffix}'
var schedulerPrivateEndpointName = 'pep-dts-${resourceNameSuffix}'
var schedulerPrivateDnsVirtualNetworkLinkName = 'vnetlink-dts-${resourceNameSuffix}'
var dashboardName = 'dash-${resourceNameSuffix}'
var dashboardDefinition = replace(
  replace(
    replace(
      replace(
        replace(loadTextContent('dashboards/durable-task-overview.json'), '__SUBSCRIPTION_ID__', subscription().subscriptionId),
        '__RESOURCE_GROUP__',
        resourceGroup().name
      ),
      '__ORCHESTRATOR_APP__',
      'ca-orchestrator-${resourceNameSuffix}'
    ),
    '__ACTIVITY_APP__',
    'ca-activity-${resourceNameSuffix}'
  ),
  '__SCHEDULER__',
  schedulerName
)

module network 'modules/network.bicep' = {
  name: 'network'
  params: {
    infrastructureSubnetName: containerAppsInfrastructureSubnetName
    location: location
    privateEndpointSubnetName: privateEndpointSubnetName
    virtualNetworkName: virtualNetworkName
  }
}

module logAnalytics 'modules/log-analytics.bicep' = {
  name: 'log-analytics'
  params: {
    location: location
    name: logAnalyticsWorkspaceName
  }
}

module containerAppsEnvironment 'modules/container-app-environment.bicep' = {
  name: 'container-apps-environment'
  dependsOn: [
    logAnalytics
    network
  ]
  params: {
    location: location
    logAnalyticsWorkspaceName: logAnalyticsWorkspaceName
    name: containerAppsEnvironmentName
    infrastructureSubnetId: network.outputs.infrastructureSubnetId
  }
}

module containerRegistry 'modules/container-registry.bicep' = {
  name: 'container-registry'
  params: {
    location: location
    name: containerRegistryName
  }
}

module clientIdentity 'modules/managed-identity.bicep' = {
  name: 'client-identity'
  params: {
    location: location
    name: clientIdentityName
  }
}

module orchestratorIdentity 'modules/managed-identity.bicep' = {
  name: 'orchestrator-identity'
  params: {
    location: location
    name: orchestratorIdentityName
  }
}

module activityIdentity 'modules/managed-identity.bicep' = {
  name: 'activity-identity'
  params: {
    location: location
    name: activityIdentityName
  }
}

module durableTaskScheduler 'modules/durable-task-scheduler.bicep' = {
  name: 'durable-task-scheduler'
  params: {
    activityWorkerPrincipalId: activityIdentity.outputs.principalId
    clientPrincipalId: clientIdentity.outputs.principalId
    ipAllowlist: schedulerIpAllowlist
    location: location
    name: schedulerName
    orchestratorWorkerPrincipalId: orchestratorIdentity.outputs.principalId
    publicNetworkAccess: schedulerPublicNetworkAccess
    taskHubName: taskHubName
  }
}

module schedulerPrivateEndpoint 'modules/durable-task-scheduler-private-endpoint.bicep' = {
  name: 'scheduler-private-endpoint'
  params: {
    location: location
    name: schedulerPrivateEndpointName
    privateEndpointSubnetId: network.outputs.privateEndpointSubnetId
    schedulerId: durableTaskScheduler.outputs.id
    virtualNetworkId: network.outputs.id
    virtualNetworkLinkName: schedulerPrivateDnsVirtualNetworkLinkName
  }
}

module clientAcrPull 'modules/acr-pull-role-assignment.bicep' = {
  name: 'client-acr-pull'
  dependsOn: [
    containerRegistry
  ]
  params: {
    principalId: clientIdentity.outputs.principalId
    registryName: containerRegistryName
  }
}

module orchestratorAcrPull 'modules/acr-pull-role-assignment.bicep' = {
  name: 'orchestrator-acr-pull'
  dependsOn: [
    containerRegistry
  ]
  params: {
    principalId: orchestratorIdentity.outputs.principalId
    registryName: containerRegistryName
  }
}

module activityAcrPull 'modules/acr-pull-role-assignment.bicep' = {
  name: 'activity-acr-pull'
  dependsOn: [
    containerRegistry
  ]
  params: {
    principalId: activityIdentity.outputs.principalId
    registryName: containerRegistryName
  }
}

module orchestratorWorker 'modules/worker-container-app.bicep' = if (deployApps) {
  name: 'orchestrator-worker'
  dependsOn: [
    orchestratorAcrPull
    schedulerPrivateEndpoint
  ]
  params: {
    acrLoginServer: containerRegistry.outputs.loginServer
    appName: 'ca-orchestrator-${resourceNameSuffix}'
    environmentId: containerAppsEnvironment.outputs.id
    identityClientId: orchestratorIdentity.outputs.clientId
    identityId: orchestratorIdentity.outputs.id
    image: '${containerRegistry.outputs.loginServer}/durable-task-orchestrator-worker:${orchestratorWorkerImageTag}'
    maxConcurrentWorkItemsCount: 1
    maxReplicas: 1
    schedulerEndpoint: durableTaskScheduler.outputs.endpoint
    taskHubName: taskHubName
    workItemType: 'Orchestration'
  }
}

module activityWorker 'modules/worker-container-app.bicep' = if (deployApps) {
  name: 'activity-worker'
  dependsOn: [
    activityAcrPull
    schedulerPrivateEndpoint
  ]
  params: {
    acrLoginServer: containerRegistry.outputs.loginServer
    appName: 'ca-activity-${resourceNameSuffix}'
    environmentId: containerAppsEnvironment.outputs.id
    identityClientId: activityIdentity.outputs.clientId
    identityId: activityIdentity.outputs.id
    image: '${containerRegistry.outputs.loginServer}/durable-task-activity-worker:${activityWorkerImageTag}'
    maxConcurrentWorkItemsCount: 10
    maxReplicas: 3
    schedulerEndpoint: durableTaskScheduler.outputs.endpoint
    taskHubName: taskHubName
    workItemType: 'Activity'
  }
}

module clientJob 'modules/client-job.bicep' = if (deployApps) {
  name: 'client-job'
  dependsOn: [
    clientAcrPull
    schedulerPrivateEndpoint
  ]
  params: {
    acrLoginServer: containerRegistry.outputs.loginServer
    environmentId: containerAppsEnvironment.outputs.id
    identityClientId: clientIdentity.outputs.clientId
    identityId: clientIdentity.outputs.id
    image: '${containerRegistry.outputs.loginServer}/durable-task-client:${clientImageTag}'
    jobName: 'job-client-${resourceNameSuffix}'
    location: location
    schedulerEndpoint: durableTaskScheduler.outputs.endpoint
    scheduleCronExpression: clientScheduleCronExpression
    taskHubName: taskHubName
  }
}

module dashboard 'modules/grafana-dashboard.bicep' = {
  name: 'durable-task-dashboard'
  params: {
    location: location
    name: dashboardName
    serializedData: dashboardDefinition
  }
}

output containerRegistryLoginServer string = containerRegistry.outputs.loginServer
output clientJobName string = 'job-client-${resourceNameSuffix}'
output dashboardId string = dashboard.outputs.id
output schedulerEndpoint string = durableTaskScheduler.outputs.endpoint
