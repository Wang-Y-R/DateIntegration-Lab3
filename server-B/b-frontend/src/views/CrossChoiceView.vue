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
          <button type="button" class="primary" @click="submitCurrent">提交请求</button>
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
                <button
                  v-if="isChosen(row)"
                  type="button"
                  class="action-btn action-danger"
                  @click="dropChosenCourse(row)"
                  :disabled="loading.courses || submitting"
                >
                  退课并提交
                </button>
                <button
                  v-else
                  type="button"
                  class="action-btn action-primary"
                  @click="useCourse(row)"
                  :disabled="loading.courses || submitting"
                >
                  选课并提交
                </button>
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
import { computed, onBeforeUnmount, onMounted, reactive, ref } from "vue";
import { CHOICE_UPDATE_EVENT, emitChoiceUpdate, requestJson } from "../api";

const baseUrl = import.meta.env.VITE_API_BASE || "http://localhost:8082";

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
const myChoices = ref([]);
const user = ref(null);
const loading = reactive({ courses: false });
const submitting = ref(false);
const message = reactive({ text: "", ok: true });
const selectedCourse = ref(null);

const resolveSno = () => form.sid || "";

const chosenIdSet = computed(() => new Set(myChoices.value.map((row) => row.id)));

const isChosen = (row) => chosenIdSet.value.has(row.id);

const generateXml = () => {
  const profile = user.value?.profile || user.value || {};
  const origin = profile.origin || profile.Origin || "";
  const xml = `<?xml version="1.0" encoding="UTF-8"?>\n<CrossDepartmentChoice>\n  <Student>\n    <Sno>${form.sid}</Sno>\n    <Snm>${form.name}</Snm>\n    <Sex>${form.sex}</Sex>\n    <Sde>${form.major}</Sde>${origin ? `\n    <Origin>${origin}</Origin>` : ""}\n  </Student>\n  <Choice>\n    <Cid>${form.cid}</Cid>\n    <Sno>${form.sid}</Sno>\n    <Grd>${form.score}</Grd>\n  </Choice>\n</CrossDepartmentChoice>`;
  xmlPayload.value = xml;
  return xml;
};

const submitRequest = async () => {
  console.log("submitRequest start", {
    baseUrl,
    action: form.action,
    destination: form.destination,
    sid: form.sid,
    cid: form.cid,
    score: form.score,
    xmlPayload: xmlPayload.value,
  });
  message.text = "";
  const xml = xmlPayload.value || generateXml();
  submitting.value = true;
  if (!baseUrl) {
    message.ok = false;
    message.text = "未配置集成服务器地址，已保存申请草稿。";
    submitting.value = false;
    return;
  }
  try {
    const endpoint = form.action === "drop" ? "/api/proxy/integrated/course/drop" : "/api/proxy/integrated/course/choose";
    console.log("submitRequest fetch", `${baseUrl}${endpoint}`);
    const res = await fetch(`${baseUrl}${endpoint}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/xml; charset=UTF-8",
        SourceSystem: "B",
        DestinationSystem: form.destination
      },
      body: xml
    });
    const text = await res.text();
    console.log("submitRequest response", res.status, text);
    message.ok = res.ok;
    message.text = res.ok ? "请求已发送，正在获取课程列表。" : "请求失败，请检查接口。";
    if (res.ok) {
      await syncCrossChoiceMirror();
      // refresh shared courses list
      await loadSharedCourses();
      await loadMyChoices();
      emitChoiceUpdate();
      // try to refresh local student's choices so UI reflects newly added course
      try {
        const choicesRes = await fetch(`${baseUrl}/api/local/choices?sno=${encodeURIComponent(form.sid)}`);
        if (choicesRes.ok) {
          const json = await choicesRes.json();
          // json structure: { code, message, data }
          const data = json?.data || null;
          if (data) {
            message.text = `请求已处理。当前已选 ${Array.isArray(data) ? data.length : 'N'} 门课程`;
          }
        }
      } catch (e) {
        // ignore
      }
    }
  } catch (err) {
    message.ok = false;
    message.text = err?.message || "网络错误";
  } finally {
    submitting.value = false;
  }
};

const useCourse = async (row) => {
  console.log("useCourse selected:", row);
  selectedCourse.value = row;
  form.cid = row.id || "";
  form.action = "choose";
  generateXml();
  message.ok = true;
  message.text = `已选择课程 ${form.cid} ${row.name || ""}`;
  await submitRequest();
};

const dropChosenCourse = async (row) => {
  console.log("dropChosenCourse selected:", row);
  selectedCourse.value = row;
  form.cid = row.id || "";
  form.action = "drop";
  generateXml();
  message.ok = true;
  message.text = `已准备退课 ${form.cid} ${row.name || ""}`;
  await submitRequest();
};

const submitCurrent = async () => {
  console.log("submitCurrent clicked");
  await submitRequest();
};

const syncCrossChoiceMirror = async () => {
  if (form.destination === "B") {
    return;
  }
  if (!form.sid || !form.cid) {
    return;
  }
  const course = selectedCourse.value || sharedCourses.value.find((row) => row.id === form.cid);
  if (form.action === "drop") {
    try {
      await fetch(`${baseUrl}/api/local/cross-choice/sync`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          action: "drop",
          sno: form.sid,
          cno: form.cid,
          destSystem: form.destination
        })
      });
    } catch (err) {
      console.warn("syncCrossChoiceMirror drop failed", err);
    }
    return;
  }
  if (!course) {
    return;
  }
  try {
    await fetch(`${baseUrl}/api/local/cross-choice/sync`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        action: form.action,
        sno: form.sid,
        cno: form.cid,
        destSystem: form.destination,
        cnm: course.name || "",
        ctm: course.time || "",
        cpt: course.score || "",
        tec: course.teacher || "",
        pla: course.location || "",
        share: course.share || "1",
        grd: form.score || ""
      })
    });
  } catch (err) {
    console.warn("syncCrossChoiceMirror failed", err);
  }
};

const getText = (node, tag) => {
  const el = node.getElementsByTagName(tag)[0];
  return el ? el.textContent || "" : "";
};

const getFirstText = (node, tags) => {
  for (const tag of tags) {
    const value = getText(node, tag);
    if (value) {
      return value;
    }
  }
  return "";
};

const parseCourseXml = (xmlText) => {
  const parser = new DOMParser();
  const doc = parser.parseFromString(xmlText, "application/xml");
  if (doc.querySelector("parsererror")) return [];

  const nodes = Array.from(doc.getElementsByTagName("class"));
  return nodes.map((node) => ({
    id: getFirstText(node, ["id", "编号", "课程编号"]),
    name: getFirstText(node, ["name", "名称"]),
    time: getFirstText(node, ["time", "课时"]),
    score: getFirstText(node, ["score", "学分"]),
    teacher: getFirstText(node, ["teacher", "老师"]),
    location: getFirstText(node, ["location", "地点"]),
    share: getFirstText(node, ["share", "共享"])
  }));
};

const parseResponseMessage = (xmlText) => {
  const parser = new DOMParser();
  const doc = parser.parseFromString(xmlText, "application/xml");
  if (doc.querySelector("parsererror")) return "";
  const msg = doc.getElementsByTagName("Message")[0];
  return msg ? msg.textContent || "" : "";
};

const loadSharedCourses = async () => {
  if (!baseUrl) {
    message.ok = false;
    message.text = "未配置集成服务器地址，无法获取课程列表。";
    return;
  }
  loading.courses = true;
  try {
    const res = await fetch(`${baseUrl}/api/proxy/integrated/course/shared`, {
      method: "GET",
      headers: {
        SourceSystem: "B"
      }
    });
    const text = await res.text();
    const respMessage = parseResponseMessage(text);
    if (!res.ok) {
      sharedCourses.value = [];
      message.ok = false;
      message.text = respMessage || "课程列表获取失败，请检查集成接口。";
      return;
    }
    sharedCourses.value = parseCourseXml(text);
    if (!sharedCourses.value.length) {
      message.ok = false;
      message.text = respMessage || "未解析到课程数据，请确认返回格式。";
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

const normalizeChoices = (rows) =>
  rows.map((row) => ({
    id: row.CNO || row.cno || row.ID || row.id,
    source: row.SOURCE || row.source || "LOCAL",
    destSystem: row.DEST_SYSTEM || row.destSystem || ""
  }));

const loadMyChoices = async () => {
  const sno = resolveSno();
  if (!sno) {
    myChoices.value = [];
    return;
  }
  try {
    const body = await requestJson(`/api/local/choices?sno=${encodeURIComponent(sno)}`);
    myChoices.value = normalizeChoices(body.data || []);
  } catch (err) {
    myChoices.value = [];
  }
};

onMounted(() => {
  const stored = localStorage.getItem("b-user");
  const userPayload = stored ? JSON.parse(stored) : {};
  user.value = userPayload;
  const profile = userPayload?.profile || userPayload || {};
  form.sid = profile.sno || profile.SNO || form.sid;
  form.name = profile.snm || profile.name || form.name;
  form.sex = profile.sex || form.sex;
  form.major = profile.major || form.major;
  loadSharedCourses();
  loadMyChoices();
  window.addEventListener(CHOICE_UPDATE_EVENT, loadSharedCourses);
  window.addEventListener(CHOICE_UPDATE_EVENT, loadMyChoices);
});

onBeforeUnmount(() => {
  window.removeEventListener(CHOICE_UPDATE_EVENT, loadSharedCourses);
  window.removeEventListener(CHOICE_UPDATE_EVENT, loadMyChoices);
});
</script>
