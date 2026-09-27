param location string
param name string
param serializedData string

resource dashboard 'Microsoft.Dashboard/dashboards@2025-09-01-preview' = {
  name: name
  location: location
  properties: {}
  tags: {
    GrafanaDashboardTags: 'durable-task,container-apps'
  }
}

resource definition 'Microsoft.Dashboard/dashboards/dashboardDefinitions@2025-09-01-preview' = {
  parent: dashboard
  name: 'default'
  properties: {
    serializedData: serializedData
  }
}

output id string = dashboard.id
