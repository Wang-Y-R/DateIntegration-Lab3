# 集成教务系统 - 集成服务器

基于 **Java Spring Boot** 的 XML 数据集成中间件，用于整合多个异构院系教务系统（A、B、C）的课程数据。

## 技术栈

- **Java 17**
- **Spring Boot 3.2.4**
- **dom4j** — XML 解析与操作
- **XSLT** — XML 格式转换
- **XSD** — XML 结构校验

## 架构说明

集成服务器作为中间层，统一协调三个院系系统之间的数据交换。各院系系统内部采用不同的 XML 格式，集成服务器负责格式转换与路由转发。

```
院系A (8081) ─┐
              ├── 集成服务器 (8080) ── 统一格式(中间格式) ── 格式转换 ── 目标院系格式
院系B (8082) ─┤
              │
院系C (8083) ─┘
```

数据流转采用**统一中间格式**策略：
1. 源系统格式 → 统一格式（通过 XSLT）
2. 统一格式校验（通过 XSD）
3. 统一格式 → 目标系统格式（通过 XSLT）

## API 接口

### 获取共享课程

```
GET /api/integrated/course/shared
Header: SourceSystem = A|B|C
```

从其他院系获取共享课程列表，转换为请求方格式后合并返回。

### 跨院系选课

```
POST /api/integrated/course/choose
Header: SourceSystem = A|B|C
Header: DestinationSystem = A|B|C
Content-Type: application/xml
```

接收源院系的选课请求，转换为目标院系格式后转发。

### 跨院系退选

```
POST /api/integrated/course/drop
Header: SourceSystem = A|B|C
Header: DestinationSystem = A|B|C
Content-Type: application/xml
```

### 全院统计

```
GET /api/integrated/statistics
```

汇总各院系 `GET /api/internal/statistics` 返回的 JSON（`students`、`courses`、`enrollments`）。

### 格式转换（兼容保留）（测试用）

```
POST /api/integrated/transform
Content-Type: application/xml
```

将学生 XML 数据转换为统一格式。

## 项目结构

```
src/main/java/com/example/integrationServer/
├── IntegrationServerApplication.java   # Spring Boot 启动类
├── IntegrationController.java          # REST 控制器
└── XmlService.java                     # XML 转换与校验服务

src/main/resources/
├── application.yml                     # 服务配置（端口、下游服务器地址）
├── formatStudent.xsd / .xsl            # 学生数据：统一格式定义与转换
├── formatClass.xsd / .xsl              # 课程数据：统一格式定义与转换
├── formatClassChoice.xsd / .xsl        # 选课数据：统一格式定义与转换
├── studentTo{A|B|C}.xsl                # 统一格式 → 各院系学生格式
├── classTo{A|B|C}.xsl                  # 统一格式 → 各院系课程格式
└── choiceTo{A|B|C}.xsl                 # 统一格式 → 各院系选课格式
```

## 运行

```bash
mvn spring-boot:run
```

默认端口 `8080`，可通过 `application.yml` 修改。下游院系 A/B/C 分别部署在 `8081`/`8082`/`8083` 端口。

