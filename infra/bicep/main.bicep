// Microsoft Foundry / Azure ML hosting for the cost-aware router. WRITTEN, NOT RUN.
// Same resources and settings as infra/terraform (parity is checked by tests/test_iac.py).
targetScope = 'resourceGroup'

@allowed(['dev', 'prod'])
param env string
param location string = resourceGroup().location
@minLength(3)
@maxLength(10)
param prefix string = 'costrt'
param logRetentionDays int = 30
param tags object = {
  workload: 'cost-aware-llm-router'
  owner: 'ops-platform'
  data: 'synthetic'
}

var name = '${prefix}-${env}'
var flat = '${prefix}${env}'

resource logs 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: 'log-${name}'
  location: location
  tags: tags
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: logRetentionDays
  }
}

resource appi 'Microsoft.Insights/components@2020-02-02' = {
  name: 'appi-${name}'
  location: location
  tags: tags
  kind: 'other'
  properties: {
    Application_Type: 'other'
    WorkspaceResourceId: logs.id
  }
}

resource st 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: 'st${flat}'
  location: location
  tags: tags
  sku: { name: 'Standard_LRS' }
  kind: 'StorageV2'
  properties: {
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    allowSharedKeyAccess: false
    allowBlobPublicAccess: false
    sasPolicy: { sasExpirationPeriod: '01.00:00:00', expirationAction: 'Log' }
  }
}

resource kv 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: 'kv-${name}'
  location: location
  tags: tags
  properties: {
    tenantId: subscription().tenantId
    sku: { family: 'A', name: 'standard' }
    enableRbacAuthorization: true
    enablePurgeProtection: true
    softDeleteRetentionInDays: 7
  }
}

resource mlw 'Microsoft.MachineLearningServices/workspaces@2025-06-01' = {
  name: 'mlw-${name}'
  location: location
  tags: tags
  kind: 'Default'
  sku: { name: 'Basic', tier: 'Basic' }
  identity: { type: 'SystemAssigned' }
  properties: {
    friendlyName: 'Cost-aware LLM router (${env})'
    applicationInsights: appi.id
    keyVault: kv.id
    storageAccount: st.id
    systemDatastoresAuthMode: 'identity'
    hbiWorkspace: true
    publicNetworkAccess: 'Enabled'
  }
}

// Managed online endpoint: callers need an Entra ID token (no endpoint keys).
resource endpoint 'Microsoft.MachineLearningServices/workspaces/onlineEndpoints@2025-06-01' = {
  parent: mlw
  name: 'ep-${name}'
  location: location
  tags: tags
  kind: 'Managed'
  identity: { type: 'SystemAssigned' }
  properties: {
    authMode: 'AADToken'
    publicNetworkAccess: 'Enabled'
    description: 'Cost-aware LLM router. Returns the routing decision and answer; personal data stays on local tiers.'
  }
}

resource diagMlw 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'diag-mlw'
  scope: mlw
  properties: {
    workspaceId: logs.id
    logs: [{ categoryGroup: 'allLogs', enabled: true }]
  }
}

resource diagKv 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'diag-kv'
  scope: kv
  properties: {
    workspaceId: logs.id
    logs: [{ category: 'AuditEvent', enabled: true }]
  }
}

output resourceGroup string = resourceGroup().name
output workspaceName string = mlw.name
output endpointName string = endpoint.name
