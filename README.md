# 集成教务系统 - DataIntegration

XML 数据集成系统，实现多院系异构教务系统之间的数据交换与格式转换。

## 项目组成

| 模块 | 说明 |
|------|------|
| [integration-server](./integration-server/) | 集成服务器 — 中间层，统一格式转换与路由转发 |
| server-A | 院系A教务系统（待开发） |
| server-B | 院系B教务系统（待开发） |
| server-C | 院系C教务系统（待开发） |

## 开发分支

各模块在独立分支上开发，完成后合并到主分支（`master`）：

- `integration_server` — 集成服务器
- `server-A` — 院系A
- `server-B` — 院系B
- `server-C` — 院系C


## 快速开始

```bash
# 集成服务器
cd integration-server
mvn spring-boot:run
```
