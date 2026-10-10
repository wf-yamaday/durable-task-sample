param location string
param openAiLocation string
param openAiName string
param storageName string
param activityPrincipalId string
param modelName string
param modelVersion string
param deploymentSku string
param deploymentCapacity int

resource openAi 'Microsoft.CognitiveServices/accounts@2025-06-01' = {
  name: openAiName
  location: openAiLocation
  kind: 'OpenAI'
  sku: { name: 'S0' }
  properties: {
    customSubDomainName: openAiName
    disableLocalAuth: true
    publicNetworkAccess: 'Enabled'
  }
}

resource deployment 'Microsoft.CognitiveServices/accounts/deployments@2025-06-01' = {
  parent: openAi
  name: modelName
  sku: {
    name: deploymentSku
    capacity: deploymentCapacity
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: modelName
      version: modelVersion
    }
    versionUpgradeOption: 'NoAutoUpgrade'
  }
}

resource openAiRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(openAi.id, activityPrincipalId, 'openai-user')
  scope: openAi
  properties: {
    principalId: activityPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd')
  }
}

resource storage 'Microsoft.Storage/storageAccounts@2025-01-01' = {
  name: storageName
  location: location
  kind: 'StorageV2'
  sku: { name: 'Standard_LRS' }
  properties: {
    allowBlobPublicAccess: false
    allowSharedKeyAccess: false
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    publicNetworkAccess: 'Enabled'
  }
}
resource blobs 'Microsoft.Storage/storageAccounts/blobServices@2025-01-01' = {
  parent: storage
  name: 'default'
}
resource containers 'Microsoft.Storage/storageAccounts/blobServices/containers@2025-01-01' = [for name in ['input', 'results']: {
  parent: blobs
  name: name
  properties: { publicAccess: 'None' }
}]
resource inputRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(containers[0].id, activityPrincipalId, 'blob-reader')
  scope: containers[0]
  properties: {
    principalId: activityPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '2a2b9908-6ea1-4ae2-8e65-a410df84e7d1')
  }
}
resource outputRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(containers[1].id, activityPrincipalId, 'blob-contributor')
  scope: containers[1]
  properties: {
    principalId: activityPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')
  }
}

output openAiEndpoint string = openAi.properties.endpoint
output deploymentName string = deployment.name
output storageAccountUrl string = storage.properties.primaryEndpoints.blob
output storageAccountName string = storage.name
