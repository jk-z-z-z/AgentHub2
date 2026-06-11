---
name: Workspace Skill
description: Agent workspace file operations - read, write, and edit files like SOUL.md, PROFILE.md, and configuration files.
---
# Workspace Skill

你负责当前 agent 工作区内的文件操作。

## 何时使用
- 需要读取、写入或编辑 `SOUL.md`
- 需要查看或修改 `PROFILE.md`
- 需要维护 `skills.json` 或 `tools.json`
- 需要处理工作区内其他文件，但要尽量小改动

## 可用工具
- `file_list`
- `file_read`
- `file_write`
- `file_edit`

## 最佳实践
1. 先读再改
2. 优先局部修改，不要整文件重写
3. 改动前确认路径在允许范围内
4. 变更后保持内容简洁、结构清晰

## 失败处理
- 找不到文件时先确认路径是否正确
- 文件越界时不要继续修改
- 如果编辑无法精确匹配旧文本，先重新读取目标段落

## 输出要求
- 说明改了哪些文件
- 说明为什么这样改
- 不要编造已写入结果