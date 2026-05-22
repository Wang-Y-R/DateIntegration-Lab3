"""
System A (院系A - 软件学院) 数据库初始化脚本
使用 SQLite 存储学生、课程、选课等数据
"""

import sqlite3
import os
import random

# 数据库文件路径：与脚本同目录下的 system_a.db
DB_PATH = os.path.join(os.path.dirname(__file__), "system_a.db")


def get_db():
    """获取数据库连接，设置 row_factory 以支持字典式访问"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化数据库：创建表并插入种子数据"""

    conn = get_db()
    cursor = conn.cursor()

    # ========== 1. 创建表 ==========
    # 如果表已存在则先删除，确保数据干净
    cursor.execute("DROP TABLE IF EXISTS choice")
    cursor.execute("DROP TABLE IF EXISTS student")
    cursor.execute("DROP TABLE IF EXISTS course")
    cursor.execute("DROP TABLE IF EXISTS account")

    # 账户表：存储系统登录账户信息
    cursor.execute("""
        CREATE TABLE account (
            账户名 VARCHAR(10) PRIMARY KEY,
            密码   VARCHAR(6),
            权限   CHAR(4)
        )
    """)

    # 学生表：存储学生基本信息，关联账户表
    cursor.execute("""
        CREATE TABLE student (
            学号     VARCHAR(12) PRIMARY KEY,
            姓名     VARCHAR(10),
            性别     VARCHAR(2),
            院系     VARCHAR(10),
            关联账户 VARCHAR(10),
            FOREIGN KEY (关联账户) REFERENCES account(账户名)
        )
    """)

    # 课程表：存储课程信息，共享标记用于跨院系选课
    cursor.execute("""
        CREATE TABLE course (
            课程编号 VARCHAR(8) PRIMARY KEY,
            课程名称 VARCHAR(10),
            学分     VARCHAR(2),
            授课老师 VARCHAR(10),
            授课地点 VARCHAR(20),
            共享     CHAR(1)
        )
    """)

    # 选课表：记录学生选课关系，课程编号+学生编号唯一
    cursor.execute("""
        CREATE TABLE choice (
            课程编号 VARCHAR(8),
            学生编号 VARCHAR(12),
            成绩     VARCHAR(3),
            UNIQUE(课程编号, 学生编号)
        )
    """)

    # ========== 2. 插入账户种子数据 ==========
    # 管理员账户
    cursor.execute(
        "INSERT INTO account (账户名, 密码, 权限) VALUES (?, ?, ?)",
        ("admin", "123456", "管理员"),
    )

    # 50 个学生账户，账户名为学号，初始密码统一为 123456
    for i in range(1, 51):
        学号 = f"A2023{i:03d}"
        cursor.execute(
            "INSERT INTO account (账户名, 密码, 权限) VALUES (?, ?, ?)",
            (学号, "123456", "学生"),
        )

    # ========== 3. 插入学生种子数据 ==========
    # 50 名学生，学号 A2023001 ~ A2023050，院系统一为软件学院
    # 姓名使用常见中文名，性别男女交替
    student_names = [
        "张伟",
        "王芳",
        "李强",
        "刘洋",
        "陈静",
        "杨帆",
        "赵敏",
        "黄磊",
        "周婷",
        "吴昊",
        "徐明",
        "孙丽",
        "马超",
        "朱颖",
        "胡杰",
        "郭琳",
        "何涛",
        "林娜",
        "高峰",
        "罗雪",
        "梁宇",
        "宋佳",
        "郑凯",
        "谢瑶",
        "韩飞",
        "唐梅",
        "冯刚",
        "董萍",
        "萧远",
        "程思",
        "曹阳",
        "袁露",
        "邓鑫",
        "许晴",
        "傅雷",
        "沈悦",
        "曾锐",
        "彭慧",
        "吕浩",
        "苏婉",
        "蒋博",
        "蔡颖",
        "贾楠",
        "丁宁",
        "魏彬",
        "薛蕾",
        "叶辉",
        "阎军",
        "余芬",
        "潘达",
    ]

    for i, name in enumerate(student_names):
        学号 = f"A2023{i + 1:03d}"
        性别 = "男" if i % 2 == 0 else "女"
        cursor.execute(
            "INSERT INTO student (学号, 姓名, 性别, 院系, 关联账户) VALUES (?, ?, ?, ?, ?)",
            (学号, name, 性别, "软件学院", 学号),
        )

    # ========== 4. 插入课程种子数据 ==========
    # 10 门软件学院课程，其中 6 门标记为共享（Y），4 门不共享（N）
    courses = [
        ("A0001", "数据结构", "4", "李教授", "教学楼A-301", "Y"),
        ("A0002", "操作系统", "4", "王教授", "教学楼A-302", "Y"),
        ("A0003", "计算机网络", "3", "张教授", "教学楼A-303", "Y"),
        ("A0004", "数据库原理", "3", "刘教授", "教学楼B-201", "Y"),
        ("A0005", "编译原理", "3", "陈教授", "教学楼B-202", "Y"),
        ("A0006", "软件工程", "3", "杨教授", "教学楼B-203", "Y"),
        ("A0007", "人工智能", "3", "赵教授", "实验楼C-101", "N"),
        ("A0008", "算法设计", "3", "黄教授", "实验楼C-102", "N"),
        ("A0009", "计算机图形学", "2", "周教授", "实验楼C-103", "N"),
        ("A0010", "信息安全", "2", "吴教授", "实验楼C-104", "N"),
    ]

    for c in courses:
        cursor.execute(
            "INSERT INTO course (课程编号, 课程名称, 学分, 授课老师, 授课地点, 共享) VALUES (?, ?, ?, ?, ?, ?)",
            c,
        )

    # ========== 5. 插入选课种子数据 ==========
    # 每位学生随机选修 5 门课程，成绩暂为空
    # 使用固定随机种子保证结果可复现
    random.seed(42)
    course_ids = [f"A{i:04d}" for i in range(1, 11)]

    for i in range(1, 51):
        学号 = f"A2023{i:03d}"
        # 从 10 门课中随机选 5 门
        selected = random.sample(course_ids, 5)
        for cid in selected:
            cursor.execute(
                "INSERT INTO choice (课程编号, 学生编号, 成绩) VALUES (?, ?, ?)",
                (cid, 学号, ""),
            )

    # ========== 6. 提交事务并关闭连接 ==========
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print("Database initialized successfully")
