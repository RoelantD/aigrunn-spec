param name string
param location string
param tags object
param workhorseDeploymentName string
param workhorseModelName string
param workhorseModelVersion string
param workhorseCapacity int
param deployClaude bool
param escalationDeploymentName string
param escalationModelName string
param escalationModelVersion string
param escalationCapacity int
param claudeOrganizationName string
param claudeCountryCode string
param claudeIndustry string

resource account 'Microsoft.CognitiveServices/accounts@2025-10-01-preview' = {
  name: name
  location: location
  tags: tags
  kind: 'AIServices'
  sku: { name: 'S0' }
  identity: { type: 'SystemAssigned' }
  properties: {
    customSubDomainName: name
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: true // Entra ID only (Constitution: prefer Entra over keys)
    allowProjectManagement: true
  }
}

resource workhorse 'Microsoft.CognitiveServices/accounts/deployments@2025-10-01-preview' = {
  parent: account
  name: workhorseDeploymentName
  sku: { name: 'GlobalStandard', capacity: workhorseCapacity }
  properties: {
    model: { format: 'OpenAI', name: workhorseModelName, version: workhorseModelVersion }
    versionUpgradeOption: 'NoAutoUpgrade'
  }
}

resource escalation 'Microsoft.CognitiveServices/accounts/deployments@2025-10-01-preview' = if (deployClaude) {
  parent: account
  name: escalationDeploymentName
  dependsOn: [workhorse] // deployments on one account are created sequentially
  sku: { name: 'GlobalStandard', capacity: escalationCapacity }
  properties: {
    model: { format: 'Anthropic', name: escalationModelName, version: escalationModelVersion }
    modelProviderData: {
      organizationName: claudeOrganizationName
      countryCode: claudeCountryCode
      industry: claudeIndustry
    }
    versionUpgradeOption: 'OnceNewDefaultVersionAvailable'
    raiPolicyName: 'Microsoft.DefaultV2'
  }
}

output name string = account.name
output openAiEndpoint string = 'https://${name}.openai.azure.com/'
output servicesEndpoint string = 'https://${name}.services.ai.azure.com/'
