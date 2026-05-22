# 系统C 使用说明

## 安装与启动

1. 安装依赖：`pip install -r requirements.txt`
2. 启动集成服务器（由课程方提供，默认 `http://localhost:8080`）
3. 启动系统C：`python app.py`
4. 登录账号：`admin / 123456`
5. 首次进入后，在「初始化」页点击「初始化示例数据」

## 集成服务器对接

### 系统C 作为客户端（调用集成服务器 JSON API）

| 功能 | 方法 | 路径 |
|------|------|------|
| 获取全院共享课程 | GET | `/api/integrated/courses` |
| 提交跨院选课 | POST | `/api/integrated/select` |
| 跨院退选 | POST | `/api/integrated/drop` |
| 全院统计 | GET | `/api/integrated/statistics` |

在 GUI「集成服务器」页配置服务器地址后，可拉取外院课程、提交选课/退选并刷新统计。

### 系统C 作为 Provider（供集成服务器回调 XML API）

| 功能 | 方法 | 路径 |
|------|------|------|
| 提供本院共享课程 | GET | `/api/provider/courses` |
| 接收外院学生选本院课 | POST | `/api/provider/receiveSelection` |

在「集成服务器」页点击「启动本院 Provider 服务」（默认端口 `5001`），集成服务器即可拉取本院课程并推送外院选课记录。

## 功能覆盖

- GUI + 登录
- MySQL 建表与初始化 50 名学生、10 门课程、每人 5 门课
- 基于 XML 的共享课程导出/导入（离线演示）
- HTTP 集成服务器对接（在线集成）
- 跨院选课信息导出/导入
- 集成统计与退选流程
