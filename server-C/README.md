# 系统C 使用说明

## 安装与启动

1. 安装依赖：`pip install -r requirements.txt`
2. 启动集成服务器：`cd integration-server && mvn spring-boot:run`（端口 **8080**）
3. （可选）启动院系 A：`cd server-A && python app.py`（端口 **8081**）
4. 启动系统 C：`python app.py`
5. 登录账号：`admin / 123456`
6. 首次进入后，在「初始化」页点击「初始化示例数据」

登录成功后会**自动启动**本院 Internal API（默认端口 **8083**，与 `integration-server` 的 `application.yml` 中 `servers.C.url` 一致）。

## 与集成服务器对接（XML，与院系 A 一致）

### 系统 C 作为客户端

| 功能 | 方法 | 路径 |
|------|------|------|
| 获取外院共享课程 | GET | `/api/integrated/course/shared`（Header: `SourceSystem: C`） |
| 提交跨院选课 | POST | `/api/integrated/course/choose`（XML + `SourceSystem` / `DestinationSystem`） |
| 跨院退选 | POST | `/api/integrated/course/drop` |
| 全院统计 | GET | `/api/integrated/statistics`（JSON） |

在 GUI「集成服务器」页配置地址 `http://localhost:8080` 后，可拉取外院课程、提交选课/退选并刷新统计。

### 系统 C 作为 Provider（供集成服务器回调）

| 功能 | 方法 | 路径 |
|------|------|------|
| 提供本院共享课程 | GET | `/api/internal/course/shared` |
| 接收外院学生选本院课 | POST | `/api/internal/course/choose` |
| 接收外院退选 | POST | `/api/internal/course/drop` |
| 本院统计 | GET | `/api/internal/statistics` |

## 功能覆盖

- GUI + 登录
- MySQL 建表与初始化 50 名学生、10 门课程、每人 5 门课
- 基于 XML 的共享课程导出/导入（离线演示）
- HTTP 集成服务器对接（在线 XML 集成）
- 跨院选课信息导出/导入
- 集成统计与退选流程

## 联通自检

1. 集成服务器、院系 A、系统 C 均已启动  
2. 浏览器打开 http://localhost:8080 应显示 API 说明页（不是错误；旧版才会 404）  
3. 系统 C 登录后 Internal API 在 8083 运行  
4. 「从服务器拉取共享课程」能导入 A 院系课程（如 `A0001`）  
5. 「刷新集成服务器统计」显示汇总（B 未部署时 `warnings` 可忽略）

## 常见问题

| 现象 | 原因 | 处理 |
|------|------|------|
| 访问 `localhost:8080` 显示 404 | 直接访问根路径，旧版无首页 | 重启集成服务器；或访问 `/health`、`/api/integrated/statistics` |
| 拉取课程 `Unknown column 'Cno'` | 远程 MySQL 表是旧结构 | 「初始化」页点击 **初始化示例数据** 重建表 |
| 拉取到 0 门课 | 院系 A 未启动 | 先 `cd server-A && python app.py` |
