param acrLoginServer string
param environmentId string
param identityClientId string
param identityId string
param image string
param jobName string
param location string
param schedulerEndpoint string
param taskHubName string

resource job 'Microsoft.App/jobs@2025-01-01' = {
  name: jobName
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${identityId}': {}
    }
  }
  properties: {
    environmentId: environmentId
    configuration: {
      triggerType: 'Manual'
      replicaTimeout: 600
      replicaRetryLimit: 0
      manualTriggerConfig: {
        parallelism: 1
        replicaCompletionCount: 1
      }
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
          name: 'client'
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
    }
  }
}

output name string = job.name
