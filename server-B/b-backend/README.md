# System B Backend (Spring Boot + Oracle + XML)

## 你已经具备的功能

- **B 端本院系接口（给 GUI/前端用，JSON）**
  - `POST /api/auth/login`：学生/管理员登录
  - `GET /api/local/courses`：课程列表
  - `GET /api/local/students?limit=50`：学生列表（演示用）
  - `POST /api/local/choice/choose`：本院选课
  - `POST /api/local/choice/drop`：本院退课
  - `GET /api/local/stats/overview`：本院统计（学生数/课程数/选课数/每门课被选次数）

- **B 端内部接口（给集成服务器调用）**
  - `GET /api/internal/course/shared`：返回 B 端共享课程（`SHARE='1'`）
  - `POST /api/internal/course/choose`：跨系选课落库（写入 `B_CHOICE`，必要时镜像导入学生到 `B_STUDENT`）
  - `POST /api/internal/course/drop`：跨系退课（删除 `B_CHOICE` 记录）
- **统一 XML 返回格式**：`<Response><Code/><Message/><Data/></Response>`

## 运行前准备（Oracle）

你需要准备一个 Oracle 用户（示例用 `B_SYSTEM/B_SYSTEM`），并保证 JDBC 可连接。

默认连接串在 `src/main/resources/application.yml`：

- `jdbc:oracle:thin:@localhost:1521/FREEPDB1`

你可以按自己环境修改。

启动时会自动执行：

- `classpath:db/schema-oracle.sql`
- `classpath:db/data-oracle.sql`

## 启动

在 `b-backend` 目录执行：

```bash
mvn spring-boot:run
```

默认端口 `8082`。

## 调用示例

### 0) 登录（JSON）

`POST http://localhost:8082/api/auth/login`

Body（学生）：

```json
{ "type": "STUDENT", "username": "B2023001", "password": "123456" }
```

Body（管理员）：

```json
{ "type": "ADMIN", "username": "admin", "password": "admin123" }
```

### 1) 获取共享课程

请求：

`GET http://localhost:8082/api/internal/course/shared`

返回的 `Data` 内部为 B 端格式：

```xml
<Classes>
  <class>
    <编号>B001</编号>
    <名称>高等数学</名称>
    <课时>32</课时>
    <学分>4</学分>
    <老师>张三</老师>
    <地点>一教-101</地点>
    <共享>Y</共享>
  </class>
</Classes>
```

### 2) 跨系选课

请求：

`POST http://localhost:8082/api/internal/course/choose`

Body（XML）：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<CrossDepartmentChoice>
  <Student>
    <学号>A2023001</学号>
    <姓名>张三</姓名>
    <性别>男</性别>
    <专业>软件学院</专业>
  </Student>
  <Choice>
    <课程编号>B001</课程编号>
    <学号>A2023001</学号>
    <得分></得分>
  </Choice>
</CrossDepartmentChoice>
```

### 3) 跨系退课

`POST http://localhost:8082/api/internal/course/drop`

Body 同上（只要 Choice 中的课程编号与学号字段有值即可）。

