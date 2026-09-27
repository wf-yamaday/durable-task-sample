@allowed([
  'Activity'
  'Entity'
  'Orchestration'
])
param workItemType string

param acrLoginServer string
param appName string
param environmentId string
param identityClientId string
param identityId string
param image string
param maxConcurrentWorkItemsCount int
param maxReplicas int
param schedulerEndpoint string
param taskHubName string

resource app 'Microsoft.App/containerApps@2025-02-02-preview' = {
  name: appName
  location: resourceGroup().location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${identityId}': {}
    }
  }
  properties: {
    managedEnvironmentId: environmentId
    configuration: {
      activeRevisionsMode: 'Single'
      registries: [
        {
          identity: identityId
          server: acrLoginServer
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'worker'
          image: image
          env: [
            {
              name: 'DTS_ENDPOINT'
              value: schedulerEndpoint
            }
            {
              name: 'DTS_TASKHUB'
              value: taskHubName
            }
            {
              name: 'DTS_SECURE_CHANNEL'
              value: 'true'
            }
            {
              name: 'DTS_USE_MANAGED_IDENTITY'
              value: 'true'
            }
            {
              name: 'AZURE_CLIENT_ID'
              value: identityClientId
            }
          ]
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
        }
      ]
      scale: {
        minReplicas: 0
        maxReplicas: maxReplicas
        rules: [
          {
            name: 'durable-task-${toLower(workItemType)}'
            custom: {
              type: 'azure-durabletask-scheduler'
              identity: identityId
              metadata: {
                endpoint: schedulerEndpoint
                maxConcurrentWorkItemsCount: string(maxConcurrentWorkItemsCount)
                taskhubName: taskHubName
                workItemType: workItemType
              }
            }
          }
        ]
      }
      terminationGracePeriodSeconds: 60
    }
  }
}

output id string = app.id
