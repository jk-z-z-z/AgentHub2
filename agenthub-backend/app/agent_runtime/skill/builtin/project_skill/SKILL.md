# Project Skill

你负责项目共享代码和命令。

## 何时使用
- 需要查看项目共享代码
- 需要读取项目代码树
- 需要在沙箱里执行安装依赖、测试、构建或其他项目命令

## 可用工具
- `project_code_list`
- `project_code_read`
- `project_command_run`
- `project_deploy_run`

## 最佳实践
1. 先定位相关目录，再读取具体文件
2. 只读取回答问题所需的最小文件集
3. 默认关闭网络，只有安装依赖等确实需要时才开启 `network_enabled`
4. 优先做读操作，再做写操作
5. 部署前尽量先跑 `test_command` 或 `build_command`

## 失败处理
- 如果项目结构不清楚，先用代码列表工具确认

## 输出要求
- 简洁说明发现了什么
- 对命令结果给出可执行结论
