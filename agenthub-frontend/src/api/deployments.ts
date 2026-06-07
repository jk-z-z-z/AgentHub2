import { httpGet, httpPost, type ApiResult } from './http'
import type { Schema } from './models'

export type DeploymentRequest = Schema['DeploymentRequest']
export type DeploymentJob = Schema['DeploymentJobOut']

export async function apiCreateDeployment(body: DeploymentRequest): Promise<ApiResult<DeploymentJob>> {
  return httpPost<DeploymentJob, DeploymentRequest>('/api/v1/deployments', body)
}

export async function apiRetryDeployment(deploymentId: number): Promise<ApiResult<DeploymentJob>> {
  return httpPost<DeploymentJob, Record<string, never>>(`/api/v1/deployments/${deploymentId}/retry`, {})
}

export async function apiGetDeployment(deploymentId: number): Promise<ApiResult<DeploymentJob>> {
  return httpGet<DeploymentJob>(`/api/v1/deployments/${deploymentId}`)
}
