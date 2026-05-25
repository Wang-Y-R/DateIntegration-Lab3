# 集成教务系统 - DataIntegration

XML 数据集成系统，实现多院系异构教务系统之间的数据交换与格式转换。

## 项目组成

| 模块 | 说明 |
|------|------|
| [integration-server](./integration-server/) | 集成服务器 — 中间层，统一格式转换与路由转发 |
| [server-A](./server-A/) | 院系A教务系统（Flask + SQL Server 结构，SQLite 演示） |
| [server-B](./server-B/) | 院系B教务系统（Spring Boot + Oracle + XML 内部接口；Vue + Vite 前端） |
| [server-C](./server-C/) | 院系C教务系统（Tkinter + MySQL + XML 集成） |

## 开发分支

各模块在独立分支上开发，完成后合并到主分支（`master`）：

- `integration_server` — 集成服务器
- `server-A` — 院系A
- `server-B` — 院系B
- `server-C` — 院系C


## 快速开始

```bash
# 1. 集成服务器（8080）
cd integration-server
mvn spring-boot:run

# 2. 院系 A（8081，可选）
cd server-A
python app.py

# 3. 院系 B（后端 8082，前端 Vite）
cd server-B/b-backend
mvn spring-boot:run

cd ../b-frontend
npm install
npm run dev

# B 前端环境变量（server-B/b-frontend/.env）
# VITE_API_BASE=http://localhost:8082
# VITE_INTEGRATED_BASE=http://localhost:8080

# 4. 院系 C（GUI + Internal API 8083）
cd server-C
pip install -r requirements.txt
python app.py


```
