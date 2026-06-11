---
name: Profile Skill
description: Agent and user profile maintenance - update PROFILE.md, agent specs, and structured memory sections.
---
# Profile Skill

你负责维护 agent / user 的配置和长期记忆文件。

## 何时使用
- 需要更新用户 `PROFILE.md`
- 需要更新 agent `PROFILE.md`
- 需要维护 `agent_spec` 文件
- 需要对用户/agent 的记忆分段做结构化更新

## 可用工具
- `user_profile_write`
- `agent_spec_write`
- `agent_spec_delete`
- `agent_profile_upsert_section`

## 最佳实践
1. 优先结构化写入，不要把所有内容堆在一段
2. 更新单个 section 时只改对应 section
3. 保持语义稳定，避免无意义重写
4. 记忆内容要短、明确、可持续复用

## 失败处理
- 找不到目标 section 时先确认 section_key
- 不确定是否覆盖时先询问

## 输出要求
- 说明修改了哪个 profile 或 spec
- 说明新增/更新了哪些 section