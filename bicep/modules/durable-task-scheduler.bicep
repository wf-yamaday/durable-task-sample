param activityWorkerPrincipalId string
param clientPrincipalId string
param ipAllowlist array
param location string
param name string
param orchestratorWorkerPrincipalId string
@allowed([
  'Disabled'
  'Enabled'
])
param publicNetworkAccess string
param taskHubName string

var durableTaskDataContributorRoleId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  '0ad04412-c4d5-4796-b79c-f76d14c8d402'
)
var durableTaskWorkerRoleId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  '80d0d6b0-f522-40a4-8886-a5a11720c375'
)

resource scheduler 'Microsoft.DurableTask/schedulers@2026-02-01' = {
  name: name
  location: location
  properties: {
    ipAllowlist: ipAllowlist
    publicNetworkAccess: publicNetworkAccess
    sku: {
      name: 'Consumption'
    }
  }
}

resource taskHub 'Microsoft.DurableTask/schedulers/taskHubs@2026-02-01' = {
  parent: scheduler
  name: taskHubName
  properties: {}
}

resource clientRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(taskHub.id, clientPrincipalId, durableTaskDataContributorRoleId)
  scope: taskHub
  properties: {
    principalId: clientPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: durableTaskDataContributorRoleId
  }
}

resource orchestratorWorkerRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(taskHub.id, orchestratorWorkerPrincipalId, durableTaskWorkerRoleId)
  scope: taskHub
  properties: {
    principalId: orchestratorWorkerPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: durableTaskWorkerRoleId
  }
}

resource activityWorkerRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(taskHub.id, activityWorkerPrincipalId, durableTaskWorkerRoleId)
  scope: taskHub
  properties: {
    principalId: activityWorkerPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: durableTaskWorkerRoleId
  }
}

output endpoint string = scheduler.properties.endpoint
output id string = scheduler.id
output taskHubId string = taskHub.id
