using './main.bicep'

param workloadName = 'durabletask'
param environmentName = 'dev'
param location = 'japaneast'
// Temporary model while the GPT-5.6-luna quota request is pending.
param openAiModelName = 'gpt-5-mini'
param openAiModelVersion = '2025-08-07'
param openAiReasoningEffort = 'low'
param openAiMaxCompletionTokens = 4096
param schedulerPublicNetworkAccess = 'Enabled'
param schedulerIpAllowlist = [
  '115.162.162.234/32'
]
