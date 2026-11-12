param principalId string
param principalType string
param foundryName string
param poolName string

var openAiUser = '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd' // Cognitive Services OpenAI User
var cognitiveUser = 'a97b65f3-24c7-4388-baec-2e87135dc908' // Cognitive Services User (Claude in Foundry)
var sessionExecutor = '0fb8eba5-a2bb-4abe-b1c1-49dfad359bb0' // Azure ContainerApps Session Executor

resource account 'Microsoft.CognitiveServices/accounts@2025-10-01-preview' existing = {
  name: foundryName
}

resource pool 'Microsoft.App/sessionPools@2026-07-01' existing = {
  name: poolName
}

resource r1 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: account
  name: guid(account.id, principalId, openAiUser)
  properties: { principalId: principalId, principalType: principalType, roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', openAiUser) }
}

resource r2 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: account
  name: guid(account.id, principalId, cognitiveUser)
  properties: { principalId: principalId, principalType: principalType, roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', cognitiveUser) }
}

resource r3 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: pool
  name: guid(pool.id, principalId, sessionExecutor)
  properties: { principalId: principalId, principalType: principalType, roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', sessionExecutor) }
}
