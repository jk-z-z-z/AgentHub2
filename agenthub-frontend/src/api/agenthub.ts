import { httpGet, httpPost } from './http'

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? 'http://127.0.0.1:8000/api/v1'
const WS_BASE = (import.meta.env.VITE_WS_BASE as string | undefined) ?? 'ws://127.0.0.1:8000'

export type User = {
  id: string
  email: string
  username: string
  display_name?: string | null
  role: string
  status: string
  bio?: string | null
}

export type LoginResult = {
  access_token: string
  user: User
}

export type Group = {
  id: string
  name: string
  description?: string | null
}

export type Member = {
  id: string
  group_id: string
  kind: 'user' | 'agent' | string
  display_name: string
  user_ref?: string | null
  agent_instance_id?: string | null
  title?: string | null
}

export type Message = {
  id: string
  group_id: string
  sender_member_id: string
  message_type: string
  content: string
  reply_to_message_id?: string | null
  metadata_json: string
  created_at: string
  updated_at: string
}

export async function listGroups(): Promise<Group[]> {
  const { data } = await httpGet<Group[]>(`${API_BASE}/groups`)
  return data
}

export async function login(payload: { email: string; password: string }): Promise<LoginResult> {
  const { data } = await httpPost<LoginResult, typeof payload>(`${API_BASE}/auth/login`, payload)
  return data
}

export async function getMe(): Promise<User> {
  const { data } = await httpGet<User>(`${API_BASE}/auth/me`)
  return data
}

export async function listMembers(groupId?: string): Promise<Member[]> {
  const { data } = await httpGet<Member[]>(`${API_BASE}/members`, { group_id: groupId })
  return data
}

export async function listMessagesByGroup(groupId: string, limit = 200, order: 'asc' | 'desc' = 'asc'): Promise<Message[]> {
  const { data } = await httpGet<Message[]>(`${API_BASE}/messages`, {
    group_id: groupId,
    limit,
  })
  return order === 'desc' ? data : [...data].sort((a, b) => Number(a.id) - Number(b.id))
}

export async function sendMessage(payload: {
  group_id: string
  sender_member_id: string
  content: string
  message_type?: string
  reply_to_message_id?: string | null
  metadata_json?: string
}): Promise<Message> {
  const { data } = await httpPost<Message, object>(`${API_BASE}/messages`, {
    group_id: payload.group_id,
    sender_member_id: payload.sender_member_id,
    message_type: payload.message_type ?? 'text',
    content: payload.content,
    reply_to_message_id: payload.reply_to_message_id ?? null,
    metadata_json: payload.metadata_json ?? '{}',
  })
  return data
}

export function buildGroupWebSocketUrl(groupId: string): string {
  const token = localStorage.getItem('token') || ''
  return `${WS_BASE}/ws/groups/${groupId}?token=${encodeURIComponent(token)}`
}
