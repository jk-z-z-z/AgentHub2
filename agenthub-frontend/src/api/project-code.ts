import { httpGet, type ApiResult } from './http'
import type { Group, ProjectCodeEntry, TextFile } from './models'

export async function apiListProjectCode(groupId: string): Promise<ApiResult<ProjectCodeEntry[]>> {
  return httpGet<ProjectCodeEntry[]>(`/api/v1/project-code/${groupId}`)
}

export async function apiReadProjectCodeFile(groupId: string, path: string): Promise<ApiResult<TextFile>> {
  return httpGet<TextFile>(`/api/v1/project-code/${groupId}/${path}`)
}

export type { Group, ProjectCodeEntry, TextFile } from './models'
