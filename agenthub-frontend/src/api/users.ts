import { httpGet, httpPost, httpPut, type ApiResult } from './http'
import type { User, UserCreateRequest, UserProfileMdOut, UserSelfUpdate } from './models'

export async function apiListUsers(q?: string): Promise<ApiResult<User[]>> {
  return httpGet<User[]>('/api/v1/users', { q })
}

export async function apiCreateUser(body: {
  email: string
  username: string
  display_name: string | null
  password: string
  role: string
  status: string
  bio: string
}): Promise<ApiResult<User>> {
  return httpPost<User, UserCreateRequest>('/api/v1/users', body)
}

export async function apiGetCurrentUser(): Promise<ApiResult<User>> {
  return httpGet<User>('/api/v1/users/me')
}

export async function apiUpdateCurrentUser(body: UserSelfUpdate): Promise<ApiResult<User>> {
  return httpPut<User, UserSelfUpdate>('/api/v1/users/me', body)
}

export async function apiGetCurrentUserProfileMd(): Promise<ApiResult<UserProfileMdOut>> {
  return httpGet<UserProfileMdOut>('/api/v1/users/me/profile-md')
}

export async function apiUpdateCurrentUserProfileMd(content: string): Promise<ApiResult<UserProfileMdOut>> {
  return httpPut<UserProfileMdOut, UserProfileMdOut>('/api/v1/users/me/profile-md', { content })
}

export type { User, UserCreateRequest, UserSelfUpdate } from './models'
