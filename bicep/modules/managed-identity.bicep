param location string
param name string

resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: name
  location: location
}

output clientId string = identity.properties.clientId
output id string = identity.id
output principalId string = identity.properties.principalId
