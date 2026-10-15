param location string
param name string
param privateEndpointSubnetId string
param targetResourceId string
param groupId string
param virtualNetworkId string
param privateDnsZoneNames array

resource zones 'Microsoft.Network/privateDnsZones@2024-06-01' = [for zoneName in privateDnsZoneNames: {
  name: zoneName
  location: 'global'
}]

resource links 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = [for (zoneName, index) in privateDnsZoneNames: {
  parent: zones[index]
  name: 'workload-vnet'
  location: 'global'
  properties: {
    registrationEnabled: false
    virtualNetwork: { id: virtualNetworkId }
  }
}]

resource endpoint 'Microsoft.Network/privateEndpoints@2024-05-01' = {
  name: name
  location: location
  properties: {
    subnet: { id: privateEndpointSubnetId }
    privateLinkServiceConnections: [
      {
        name: groupId
        properties: {
          groupIds: [groupId]
          privateLinkServiceId: targetResourceId
        }
      }
    ]
  }
}

resource zoneGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-05-01' = {
  parent: endpoint
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [for (zoneName, index) in privateDnsZoneNames: {
      name: replace(zoneName, '.', '-')
      properties: { privateDnsZoneId: zones[index].id }
    }]
  }
}

output id string = endpoint.id
