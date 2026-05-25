<template>
  <section class="view">
    <header class="view-header">
      <div>
        <p class="eyebrow">课程中心</p>
        <h1>课程列表</h1>
        <p class="subtitle">本学期课程已开放，支持校内与跨系共享课程查询。</p>
      </div>
      <button class="ghost" @click="refreshAll" :disabled="loadingList || loadingChoices">
        {{ loadingList || loadingChoices ? '加载中...' : '刷新数据' }}
      </button>
    </header>

    <div class="card">
      <div class="info-strip">
        <div class="info-item">
          <span class="info-label">当前学期</span>
          <span class="info-value">2025-2026-2</span>
        </div>
        <div class="info-item">
          <span class="info-label">学生</span>
          <span class="info-value">{{ snoDisplay }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">已选课程</span>
          <span class="info-value">{{ myCourses.length }} 门</span>
        </div>
        <div class="info-item">
          <span class="info-label">已选学分</span>
          <span class="info-value">{{ totalSelectedCredits }}</span>
        </div>
      </div>
      <div class="toolbar">
        <input v-model="keyword" placeholder="按课程名 / 教师 / 编号搜索" />
        <select v-model="shareFilter">
          <option value="all">全部课程</option>
          <option value="shared">共享课程</option>
          <option value="local">不共享</option>
        </select>
        <span class="muted">共 {{ filteredCourses.length }} 门课程</span>
      </div>
      <table class="data-table" v-if="filteredCourses.length">
        <thead>
          <tr>
            <th>课程编号</th>
            <th>课程名称</th>
            <th>课时</th>
            <th>学分</th>
            <th>教师</th>
            <th>地点</th>
            <th>共享</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in filteredCourses" :key="row.id">
            <td>{{ row.id }}</td>
            <td>{{ row.name }}</td>
            <td>{{ row.time }}</td>
            <td>{{ row.score }}</td>
            <td>{{ row.teacher }}</td>
            <td>{{ row.location }}</td>
            <td>
              <span class="badge" :class="row.share === '1' || row.share === 'Y' ? 'ok' : 'warn'">
                {{ row.share === '1' || row.share === 'Y' ? '共享' : '不共享' }}
              </span>
            </td>
            <td>
              <div class="button-row">
                <button
                  class="action-btn action-primary"
                  @click="chooseCourse(row)"
                  :disabled="loadingAction || isChosen(row)"
                >
                  选课
                </button>
                <button
                  class="action-btn action-danger"
                  @click="dropCourse(row)"
                  :disabled="loadingAction || !isChosen(row)"
                >
                  退课
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-else class="muted">暂无课程数据。</p>
      <p class="message" :class="message.ok ? 'ok' : 'error'" v-if="message.text">
        {{ message.text }}
      </p>
    </div>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from "vue";
import { CHOICE_UPDATE_EVENT, emitChoiceUpdate, apiBaseUrl, requestJson } from "../api";

const loadingList = ref(false);
const loadingChoices = ref(false);
const loadingAction = ref(false);
const courses = ref([]);
const keyword = ref("");
const shareFilter = ref("all");
const user = ref(null);
const myCourses = ref([]);
const message = reactive({ text: "", ok: true });

const normalizeCourses = (rows) =>
  rows.map((row) => ({
    id: row.ID || row.id || row.CNO || row.cno,
    name: row.NAME || row.name,
    time: row.TIME || row.time,
    score: row.SCORE || row.score,
    teacher: row.TEACHER || row.teacher,
    location: row.LOCATION || row.location,
    share: row.SHARE || row.share
  }));

const loadCourses = async () => {
  loadingList.value = true;
  try {
    const body = await requestJson("/api/local/courses");
    courses.value = normalizeCourses(body.data || []);
    message.text = "";
  } catch (err) {
    courses.value = [];
    message.ok = false;
    message.text = err?.message || "课程加载失败";
  } finally {
    loadingList.value = false;
  }
};

const normalizeChoiceCourses = (rows) =>
  rows.map((row) => ({
    id: row.CNO || row.cno || row.ID || row.id,
    name: row.CNM || row.cnm || row.NAME || row.name,
    time: row.CTM || row.ctm || row.TIME || row.time,
    score: row.CPT || row.cpt || row.SCORE || row.score,
    teacher: row.TEC || row.tec || row.TEACHER || row.teacher,
    location: row.PLA || row.pla || row.LOCATION || row.location,
    share: row.SHARE || row.share,
    source: row.SOURCE || row.source || "LOCAL",
    destSystem: row.DEST_SYSTEM || row.destSystem || ""
  }));

const loadMyChoices = async () => {
  const sno = resolveSno();
  if (!sno) {
    myCourses.value = [];
    return;
  }
  loadingChoices.value = true;
  try {
    const body = await requestJson(`/api/local/choices?sno=${encodeURIComponent(sno)}`);
    myCourses.value = normalizeChoiceCourses(body.data || []);
  } catch (err) {
    myCourses.value = [];
  } finally {
    loadingChoices.value = false;
  }
};

const refreshAll = async () => {
  await Promise.all([loadCourses(), loadMyChoices()]);
};

const resolveSno = () => {
  const payload = user.value || {};
  return payload?.userId || payload?.profile?.sno || payload?.profile?.SNO || payload?.sno || "";
};

const snoDisplay = computed(() => resolveSno() || "未登录");

const chosenIdSet = computed(() => new Set(myCourses.value.map((row) => row.id)));

const isChosen = (row) => chosenIdSet.value.has(row.id);

const totalSelectedCredits = computed(() =>
  myCourses.value.reduce((sum, row) => sum + Number(row.score || 0), 0)
);

const chooseCourse = async (row) => {
  const sno = resolveSno();
  if (!sno) {
    message.ok = false;
    message.text = "请先登录学生账号。";
    return;
  }
  if (isChosen(row)) return;
  loadingAction.value = true;
  message.text = "";
  try {
    const body = await requestJson("/api/local/choice/choose", {
      method: "POST",
      body: JSON.stringify({ sno, cno: row.id })
    });
    message.ok = body.code === 200;
    message.text = body.message || (body.code === 200 ? "选课成功" : "选课失败");
    if (body.code === 200) {
      await loadMyChoices();
      emitChoiceUpdate();
    }
  } catch (err) {
    message.ok = false;
    message.text = err?.message || "网络错误";
  } finally {
    loadingAction.value = false;
  }
};

const dropCourse = async (row) => {
  const sno = resolveSno();
  if (!sno) {
    message.ok = false;
    message.text = "请先登录学生账号。";
    return;
  }
  if (!isChosen(row)) return;
  loadingAction.value = true;
  message.text = "";
  try {
    if (row.source === "CROSS") {
      await dropCrossCourse(row, sno);
      message.ok = true;
      message.text = "跨院系退课成功";
      await loadMyChoices();
      emitChoiceUpdate();
      return;
    }
    const body = await requestJson("/api/local/choice/drop", {
      method: "POST",
      body: JSON.stringify({ sno, cno: row.id })
    });
    message.ok = body.code === 200;
    message.text = body.message || (body.code === 200 ? "退课成功" : "退课失败");
    if (body.code === 200) {
      await loadMyChoices();
      emitChoiceUpdate();
    }
  } catch (err) {
    message.ok = false;
    message.text = err?.message || "网络错误";
  } finally {
    loadingAction.value = false;
  }
};

const buildCrossChoiceXml = (sno, cno, destSystem, courseRow) => {
  const profile = user.value?.profile || user.value || {};
  const studentName = profile.snm || profile.name || "";
  const sex = profile.sex || "";
  const major = profile.major || profile.Sde || "";
  const origin = profile.origin || profile.Origin || "";
  const score = courseRow?.score || "";
  return `<?xml version="1.0" encoding="UTF-8"?>\n<CrossDepartmentChoice>\n  <Student>\n    <Sno>${sno}</Sno>\n    <Snm>${studentName}</Snm>\n    <Sex>${sex}</Sex>\n    <Sde>${major}</Sde>${origin ? `\n    <Origin>${origin}</Origin>` : ""}\n  </Student>\n  <Choice>\n    <Cno>${cno}</Cno>\n    <Sno>${sno}</Sno>\n    <Grd>${score}</Grd>\n  </Choice>\n</CrossDepartmentChoice>`;
};

const dropCrossCourse = async (row, sno) => {
  const xml = buildCrossChoiceXml(sno, row.id, row.destSystem || "A", row);
  const res = await fetch(`${apiBaseUrl}/api/proxy/integrated/course/drop`, {
    method: "POST",
    headers: {
      "Content-Type": "application/xml; charset=UTF-8",
      SourceSystem: "B",
      DestinationSystem: row.destSystem || "A"
    },
    body: xml
  });
  const text = await res.text();
  if (!res.ok) {
    throw new Error(text || "跨院系退课失败");
  }
  try {
    await requestJson("/api/local/cross-choice/sync", {
      method: "POST",
      body: JSON.stringify({
        action: "drop",
        sno,
        cno: row.id,
        destSystem: row.destSystem || "A"
      })
    });
  } catch (err) {
    console.warn("mirror drop sync failed", err);
  }
};

const filteredCourses = computed(() => {
  let rows = courses.value;
  if (shareFilter.value === "shared") {
    rows = rows.filter((row) => row.share === "1" || row.share === "Y");
  } else if (shareFilter.value === "local") {
    rows = rows.filter((row) => row.share !== "1" && row.share !== "Y");
  }
  if (!keyword.value) return rows;
  const key = keyword.value.trim().toLowerCase();
  return rows.filter((row) =>
    [row.id, row.name, row.teacher].some((val) => String(val || "").toLowerCase().includes(key))
  );
});

onMounted(() => {
  const stored = localStorage.getItem("b-user");
  user.value = stored ? JSON.parse(stored) : null;
  refreshAll();
  window.addEventListener(CHOICE_UPDATE_EVENT, loadMyChoices);
});

onBeforeUnmount(() => {
  window.removeEventListener(CHOICE_UPDATE_EVENT, loadMyChoices);
});
</script>
