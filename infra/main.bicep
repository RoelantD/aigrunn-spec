// Infrastructure for the Agentic Advent of Code Solver (research.md R12).
// Provisions: Foundry (AIServices) account + GPT-6.1 Sol and Claude Opus 5.5 deployments,
// an ACA Dynamic Sessions pool (PythonLTS, egress disabled), and role assignments for the operator.
// The application itself runs locally on the presenter's laptop.
targetScope = 'subscription'

@minLength(1)
@maxLength(40)
@description('azd environment name; used to derive resource names')
param environmentName string

@description('Region that offers GPT-6.1 Sol, Claude Opus 5.5 (Global Standard) and Dynamic Sessions')
param location string = 'eastus2'

@description('Object ID of the operator (azd sets AZURE_PRINCIPAL_ID)')
param principalId string

@allowed(['User', 'ServicePrincipal'])
param principalType string = 'User'

@description('Workhorse deployment name / model / version')
param workhorseDeploymentName string = 'gpt-6.1-sol'
param workhorseModelName string = 'gpt-6.1-sol'
param workhorseModelVersion string = '2026-09-29'
@description('Global Standard capacity in thousands of tokens per minute')
param workhorseCapacity int = 100

@description('Deploy the Claude escalation model (requires Marketplace terms acceptance and an eligible subscription)')
param deployClaude bool = true
param escalationDeploymentName string = 'claude-opus-5-5'
param escalationModelName string = 'claude-opus-5-5'
param escalationModelVersion string = '1'
param escalationCapacity int = 25
@description('Legal organization name passed to the model provider (accepts Marketplace terms on your behalf)')
param claudeOrganizationName string = ''
@description('Two-letter billing country code, e.g. NL')
param claudeCountryCode string = ''
@allowed(['technology', 'finance', 'healthcare', 'education', 'retail', 'manufacturing', 'government', 'media', 'other'])
param claudeIndustry string = 'technology'

@description('Max concurrent sandbox sessions')
param maxConcurrentSessions int = 10

var token = toLower(uniqueString(subscription().id, environmentName, location))
var tags = { 'azd-env-name': environmentName, app: 'agentic-puzzle-solver' }

resource rg 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: 'rg-${environmentName}'
  location: location
  tags: tags
}

module foundry 'modules/foundry.bicep' = {
  scope: rg
  name: 'foundry'
  params: {
    name: 'aif-aps-${token}'
    location: location
    tags: tags
    workhorseDeploymentName: workhorseDeploymentName
    workhorseModelName: workhorseModelName
    workhorseModelVersion: workhorseModelVersion
    workhorseCapacity: workhorseCapacity
    deployClaude: deployClaude
    escalationDeploymentName: escalationDeploymentName
    escalationModelName: escalationModelName
    escalationModelVersion: escalationModelVersion
    escalationCapacity: escalationCapacity
    claudeOrganizationName: claudeOrganizationName
    claudeCountryCode: claudeCountryCode
    claudeIndustry: claudeIndustry
  }
}

module sessions 'modules/sessionpool.bicep' = {
  scope: rg
  name: 'sessions'
  params: {
    name: 'apspool${take(token, 12)}'
    location: location
    tags: tags
    maxConcurrentSessions: maxConcurrentSessions
  }
}

module roles 'modules/roles.bicep' = {
  scope: rg
  name: 'roles'
  params: {
    principalId: principalId
    principalType: principalType
    foundryName: foundry.outputs.name
    poolName: sessions.outputs.name
  }
}

// Values for the application's .env (see .env.example)
output AZURE_RESOURCE_GROUP string = rg.name
output FOUNDRY_OPENAI_BASE_URL string = '${foundry.outputs.openAiEndpoint}openai/v1'
output FOUNDRY_ANTHROPIC_BASE_URL string = deployClaude ? '${foundry.outputs.servicesEndpoint}anthropic' : ''
output WORKHORSE_DEPLOYMENT string = workhorseDeploymentName
output ESCALATION_DEPLOYMENT string = escalationDeploymentName
output SESSIONS_POOL_ENDPOINT string = sessions.outputs.poolManagementEndpoint
