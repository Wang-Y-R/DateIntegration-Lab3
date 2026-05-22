<template>
  <section class="view">
    <header class="view-header">
      <div>
        <p class="eyebrow">跨系服务</p>
        <h1>跨系选课</h1>
        <p class="subtitle">提交跨院系申请前请确认个人信息与目标课程。</p>
      </div>
    </header>

    <div class="grid">
      <div class="card">
        <div class="info-strip">
          <div class="info-item">
            <span class="info-label">当前院系</span>
            <span class="info-value">B 院系</span>
          </div>
          <div class="info-item">
            <span class="info-label">学号</span>
            <span class="info-value">{{ form.sid || '未登录' }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">跨系状态</span>
            <span class="info-value">申请开放</span>
          </div>
        </div>
        <div class="card-header">
          <h2>跨系申请</h2>
          <p>选择目标院系与课程，然后提交请求。</p>
        </div>
        <form class="form-columns" @submit.prevent>
          <label>
            目标院系
            <select v-model="form.destination" @change="loadSharedCourses">
              <option value="A">A 院系</option>
              <option value="C">C 院系</option>
            </select>
          </label>
          <label>
            操作类型
            <select v-model="form.action">
              <option value="choose">选课</option>
              <option value="drop">退课</option>
            </select>
          </label>
          <label>
            学号
            <input v-model="form.sid" placeholder="B2023001" readonly />
          </label>
          <label>
            姓名
            <input v-model="form.name" placeholder="张三" readonly />
          </label>
          <label>
            性别
            <select v-model="form.sex" disabled>
              <option value="男">男</option>
              <option value="女">女</option>
            </select>
          </label>
          <label>
            专业
            <input v-model="form.major" placeholder="软件工程" readonly />
          </label>
          <label>
            课程编号
            <input v-model="form.cid" placeholder="从右侧列表选择" />
          </label>
          <label>
            目标课程成绩(可空)
            <input v-model="form.score" placeholder="" />
          </label>
        </form>
        <p class="help-text">提交后会发送跨系请求，并刷新可选课程列表。</p>
        <div class="button-row">
          <button class="primary" @click="submitRequest">提交请求</button>
          <button class="ghost" @click="loadSharedCourses" :disabled="loading.courses">
            {{ loading.courses ? '加载中...' : '获取可选课程' }}
          </button>
        </div>
        <p class="message" :class="message.ok ? 'ok' : 'error'" v-if="message.text">
          {{ message.text }}
        </p>
      </div>

      <div class="card">
        <div class="card-header">
          <h2>跨院系可选课程</h2>
          <p>点击“选用”将课程编号带回申请表。</p>
        </div>
        <div class="toolbar">
          <span class="muted">目标院系：{{ form.destination }} 院系</span>
          <span class="muted">共 {{ sharedCourses.length }} 门</span>
        </div>
        <table class="data-table" v-if="sharedCourses.length">
          <thead>
            <tr>
              <th>课程编号</th>
              <th>课程名称</th>
              <th>课时</th>
              <th>学分</th>
              <th>教师</th>
              <th>地点</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in sharedCourses" :key="row.id">
              <td>{{ row.id }}</td>
              <td>{{ row.name }}</td>
              <td>{{ row.time }}</td>
              <td>{{ row.score }}</td>
              <td>{{ row.teacher }}</td>
              <td>{{ row.location }}</td>
              <td>
                <button class="action-btn action-primary" @click="useCourse(row)">选用</button>
              </td>
            </tr>
          </tbody>
        </table>
        <p v-else class="muted">暂无课程数据，请点击“获取可选课程”。</p>
      </div>
    </div>
  </section>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue";

const baseUrl = import.meta.env.VITE_INTEGRATED_BASE || "";

const form = reactive({
  destination: "A",
  action: "choose",
  sid: "",
  name: "",
  sex: "男",
  major: "",
  cid: "",
  score: ""
});

const xmlPayload = ref("");
const sharedCourses = ref([]);
const loading = reactive({ courses: false });
const message = reactive({ text: "", ok: true });

const generateXml = () => {
  const xml = `<?xml version="1.0" encoding="UTF-8"?>\n<CrossDepartmentChoice>\n  <Student>\n    <id>${form.sid}</id>\n    <name>${form.name}</name>\n    <sex>${form.sex}</sex>\n    <major>${form.major}</major>\n    <origin>B</origin>\n  </Student>\n  <Choice>\n    <cid>${form.cid}</cid>\n    <sid>${form.sid}</sid>\n    <score>${form.score}</score>\n  </Choice>\n</CrossDepartmentChoice>`;
  xmlPayload.value = xml;
  return xml;
};

const submitRequest = async () => {
  message.text = "";
  const xml = xmlPayload.value || generateXml();
  if (!baseUrl) {
    message.ok = false;
    message.text = "未配置集成服务器地址，已保存申请草稿。";
    return;
  }
  try {
    const endpoint = form.action === "drop" ? "/api/integrated/course/drop" : "/api/integrated/course/choose";
    const res = await fetch(`${baseUrl}${endpoint}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/xml; charset=UTF-8",
        DestinationSystem: form.destination
      },
      body: xml
    });
    const text = await res.text();
    message.ok = res.ok;
    message.text = res.ok ? "请求已发送，正在获取课程列表。" : "请求失败，请检查接口。";
    if (res.ok) {
      await loadSharedCourses();
    }
  } catch (err) {
    message.ok = false;
    message.text = err?.message || "网络错误";
  }
};

const useCourse = (row) => {
  form.cid = row.id || "";
};

const getText = (node, tag) => {
  const el = node.getElementsByTagName(tag)[0];
  return el ? el.textContent || "" : "";
};

const parseCourseXml = (xmlText) => {
  const parser = new DOMParser();
  const doc = parser.parseFromString(xmlText, "application/xml");
  if (doc.querySelector("parsererror")) return [];
  let nodes = Array.from(doc.getElementsByTagName("class"));
  if (!nodes.length) nodes = Array.from(doc.getElementsByTagName("Class"));
  return nodes.map((node) => ({
    id: getText(node, "id"),
    name: getText(node, "name"),
    time: getText(node, "time"),
    score: getText(node, "score"),
    teacher: getText(node, "teacher"),
    location: getText(node, "location"),
    share: getText(node, "share")
  }));
};

const loadSharedCourses = async () => {
  if (!baseUrl) {
    message.ok = false;
    message.text = "未配置集成服务器地址，无法获取课程列表。";
    return;
  }
  loading.courses = true;
  try {
    const res = await fetch(`${baseUrl}/api/integrated/course/list`, {
      method: "GET",
      headers: {
        DestinationSystem: form.destination
      }
    });
    const text = await res.text();
    if (!res.ok) {
      sharedCourses.value = [];
      message.ok = false;
      message.text = "课程列表获取失败，请检查集成接口。";
      return;
    }
    sharedCourses.value = parseCourseXml(text);
    if (!sharedCourses.value.length) {
      message.ok = false;
      message.text = "未解析到课程数据，请确认返回格式。";
      return;
    }
    message.text = "";
  } catch (err) {
    sharedCourses.value = [];
    message.ok = false;
    message.text = err?.message || "网络错误";
  } finally {
    loading.courses = false;
  }
};

onMounted(() => {
  const stored = localStorage.getItem("b-user");
  const userPayload = stored ? JSON.parse(stored) : {};
  const profile = userPayload?.profile || userPayload || {};
  form.sid = profile.sno || profile.SNO || form.sid;
  form.name = profile.snm || profile.name || form.name;
  form.sex = profile.sex || form.sex;
  form.major = profile.major || form.major;
  loadSharedCourses();
});
</script>
