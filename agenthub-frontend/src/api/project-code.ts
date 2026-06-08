import { httpDelete, httpGet, httpPost, httpPut, type ApiResult } from './http'
import type { Group, ProjectCodeEntry, TextFile } from './models'

export async function apiListProjectCode(groupId: string): Promise<ApiResult<ProjectCodeEntry[]>> {
  return httpGet<ProjectCodeEntry[]>(`/api/v1/project-code/${groupId}`)
}

export async function apiReadProjectCodeFile(groupId: string, path: string): Promise<ApiResult<TextFile>> {
  return httpGet<TextFile>(`/api/v1/project-code/${groupId}/${path}`)
}

export async function apiWriteProjectCodeFile(
  groupId: string,
  path: string,
  content: string,
): Promise<ApiResult<TextFile>> {
  return httpPut<TextFile, { content: string }>(`/api/v1/project-code/${groupId}/${path}`, { content })
}

export async function apiCreateProjectCodeDir(
  groupId: string,
  path: string,
): Promise<ApiResult<ProjectCodeEntry>> {
  return httpPost<ProjectCodeEntry, { path: string }>(`/api/v1/project-code/${groupId}/directories`, { path })
}

export async function apiDeleteProjectCodeEntry(
  groupId: string,
  path: string,
): Promise<ApiResult<ProjectCodeEntry>> {
  return httpDelete<ProjectCodeEntry>(`/api/v1/project-code/${groupId}/${path}`)
}

export type { Group, ProjectCodeEntry, TextFile } from './models'
