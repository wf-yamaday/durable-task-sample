using './main.bicep'

param workloadName = 'durabletask'
param environmentName = 'dev'
param location = 'japaneast'
param schedulerPublicNetworkAccess = 'Enabled'
param schedulerIpAllowlist = [
  '115.162.162.234/32'
]
