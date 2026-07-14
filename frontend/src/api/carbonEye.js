import { apiRequest } from './client'

export function getCarbonEyeOverview() {
  return apiRequest('/api/carbon-eye/overview')
}

export function getCarbonEyeMonthlyTrends() {
  return apiRequest('/api/carbon-eye/monthly-trends')
}

export function getCarbonEyeWeather2024() {
  return apiRequest('/api/carbon-eye/weather-2024')
}

export function getCarbonEyeCarbonEmissions() {
  return apiRequest('/api/carbon-eye/carbon-emissions')
}

export function getCarbonEyeWarnings() {
  return apiRequest('/api/carbon-eye/warnings')
}

export function getCarbonEyeDailyCases() {
  return apiRequest('/api/carbon-eye/daily-cases')
}

export function getCarbonEyeMethodology() {
  return apiRequest('/api/carbon-eye/methodology')
}

export function getCarbonEyeRealtimeAqi() {
  return apiRequest('/api/carbon-eye/realtime-aqi')
}

export function getCarbonEyeParkCarbonEstimate() {
  return apiRequest('/api/carbon-eye/park-carbon-estimate')
}

export function getCarbonEyeCdci() {
  return apiRequest('/api/carbon-eye/cdci')
}

export function getCarbonEyeIndustryProfile() {
  return apiRequest('/api/carbon-eye/industry-profile')
}

export function getCarbonEyeGovernanceExplanation() {
  return apiRequest('/api/carbon-eye/governance-explanation')
}

export function getCarbonEyeParkElectricityEmissions() {
  return apiRequest('/api/carbon-eye/park-electricity-emissions')
}

export function getCarbonEyeEconomicCarbonIntensity() {
  return apiRequest('/api/carbon-eye/economic-carbon-intensity')
}

export function getCarbonEyeParkEnvironmentSnapshot() {
  return apiRequest('/api/carbon-eye/park-environment-snapshot')
}

export function getCarbonEyeWeatherLongTerm() {
  return apiRequest('/api/carbon-eye/weather-long-term')
}

export function getCarbonEyeWeatherCorrelations() {
  return apiRequest('/api/carbon-eye/weather-correlations')
}

export function getCarbonEyeCdciSensitivity() {
  return apiRequest('/api/carbon-eye/cdci-sensitivity')
}

export function getCarbonEyeDataQuality() {
  return apiRequest('/api/carbon-eye/data-quality')
}

export function getCarbonEyeSources() {
  return apiRequest('/api/carbon-eye/sources')
}
