param name string
param location string
param tags object
param maxConcurrentSessions int

// Built-in Python code interpreter sessions; outbound network disabled (Constitution II, FR-023).
resource pool 'Microsoft.App/sessionPools@2026-07-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    poolManagementType: 'Dynamic'
    containerType: 'PythonLTS'
    dynamicPoolConfiguration: {
      lifecycleConfiguration: { lifecycleType: 'Timed', cooldownPeriodInSeconds: 300 }
    }
    scaleConfiguration: { maxConcurrentSessions: maxConcurrentSessions }
    sessionNetworkConfiguration: { status: 'EgressDisabled' }
  }
}

output name string = pool.name
output poolManagementEndpoint string = pool.properties.poolManagementEndpoint
