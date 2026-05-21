# 集成教务系统 - 院系A（软件学院）

基于 **Python Flask** 的教务管理系统，提供 Web GUI 和 XML API 接口，通过集成服务器实现跨院系选课。

## 技术栈

- **Python 3.13**
- **Flask** — Web 框架
- **lxml** — XML 解析、XSD 校验、XSLT 转换
- **SQLite** — 本地数据库（Python 内置，无需额外安装）
- **uv** — 依赖管理

## 安装依赖

需要先安装 [uv](https://docs.astral.sh/uv/)，然后在本目录执行：

```bash
cd server-A
uv sync
```

会自动创建虚拟环境并安装 Flask、lxml、requests 等依赖。不需要单独安装数据库，SQLite 由 Python 标准库自带。

## 运行

```bash
cd server-A
uv run python app.py
```

服务启动在 `http://localhost:8081`。

浏览器打开 http://localhost:8081 即可进入登录页面。

> 确保集成服务器已先在 `8080` 端口启动，否则跨系选课功能不可用。

## 测试账号

| 角色 | 账户名 | 密码 |
|------|--------|------|
| 管理员 | `admin` | `123456` |
| 学生 | `A2023001` ~ `A2023050` | `123456` |

## 种子数据

首次启动自动初始化数据库：

- 50 名学生（软件学院）
- 10 门课程（6 门共享、4 门不共享）
- 每名学生 5 门选修课

## API 接口

以下接口供集成服务器调用，返回 XML。

### 获取共享课程

```
GET /api/internal/course/shared
```

返回所有标记为共享的课程列表（System A 格式 XML）。

### 跨系选课

```
POST /api/internal/course/choose
Content-Type: application/xml; charset=UTF-8
```

接收包含 `<CrossDepartmentChoice>` 的 XML，将学生信息和选课记录写入本地数据库。

### 跨系退课

```
POST /api/internal/course/drop
Content-Type: application/xml; charset=UTF-8
```

从数据库删除对应的选课记录。

## Web 页面

基于 Jinja2 模板渲染，样式内联在 HTML 中，无需额外前端构建。

| 路径 | 功能 |
|------|------|
| `/` | 登录 |
| `/dashboard` | 仪表盘（学生：个人信息 + 已选课程；管理员：统计数据） |
| `/courses` | 选课中心（选课 / 退课 / 管理员切换共享） |
| `/shared-courses` | 跨系选课（从集成服务器拉取其他院系共享课程） |
| `/admin/stats` | 管理员统计（学生数、课程数、选课人数） |

## 项目结构

```
server-A/
├── app.py              # Flask 主应用
├── db.py               # 数据库初始化与种子数据
├── templates/          # Jinja2 HTML 模板
│   ├── base.html
│   ├── login.html
│   ├── dashboard.html
│   ├── courses.html
│   ├── shared_courses.html
│   └── admin_stats.html
├── xsd/                # XML Schema（本地格式校验）
│   ├── classA.xsd
│   ├── studentA.xsd
│   └── choiceA.xsd
└── xsl/                # XSLT（本地格式 ↔ 统一格式）
    ├── classToA.xsl / classFromA.xsl
    ├── studentToA.xsl / studentFromA.xsl
    └── choiceToA.xsl / choiceFromA.xsl
```

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `INTEGRATION_SERVER` | `http://localhost:8080` | 集成服务器地址 |
