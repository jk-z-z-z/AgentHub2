import { httpDelete, httpGet, httpPost, type ApiResult } from './http'

export type PreviewRequest = {
  workspace_id: number
  source_path?: string
  sandbox_image?: string | null
  install_command?: string | null
  build_command?: string | null
  env?: Record<string, string>
  host_port?: number | null
}

export type PreviewJob = {
  id: number
  workspace_id: number
  project_id: number
  sandbox_run_id: number | null
  status: string
  container_name: string
  container_id: string | null
  sandbox_image: string
  source_path: string
  host_port: number
  preview_root_path: string | null
  url: string | null
  attempt_count: number
  logs_text: string
  error_message: string | null
  spec: Record<string, unknown>
  context: Record<string, unknown>
  result: Record<string, unknown>
  created_at: string
  updated_at: string
  started_at: string | null
  finished_at: string | null
}

export async function apiCreatePreview(body: PreviewRequest): Promise<ApiResult<PreviewJob>> {
  return httpPost<PreviewJob, PreviewRequest>('/api/v1/previews', body)
}

export async function apiGetWorkspacePreview(workspaceId: number): Promise<ApiResult<PreviewJob>> {
  return httpGet<PreviewJob>(`/api/v1/workspaces/${workspaceId}/preview`)
}

export async function apiDeleteWorkspacePreview(workspaceId: number): Promise<ApiResult<PreviewJob>> {
  return httpDelete<PreviewJob>(`/api/v1/workspaces/${workspaceId}/preview`)
}
