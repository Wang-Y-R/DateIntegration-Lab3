<template>
  <section class="view">
    <header class="view-header">
      <div>
        <p class="eyebrow">课程管理</p>
        <h1>我的课程</h1>
      </div>
      <button class="ghost" @click="loadMyCourses" :disabled="loading">
        {{ loading ? '加载中...' : '刷新数据' }}
      </button>
    </header>

    <div class="card">
      <div class="info-strip">
        <div class="info-item">
          <span class="info-label">学生</span>
          <span class="info-value">{{ sno || '未登录' }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">已选课程</span>
          <span class="info-value">{{ myCourses.length }} 门</span>
        </div>
        <div class="info-item">
          <span class="info-label">已选学分</span>
          <span class="info-value">{{ totalCredits }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">选课状态</span>
          <span class="info-value">进行中</span>
        </div>
      </div>
      <div class="toolbar">
        <span class="muted">学生：{{ sno || '未登录' }}</span>
        <span class="muted">共 {{ myCourses.length }} 门课程</span>
      </div>
      <table class="data-table" v-if="myCourses.length">
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
          <tr v-for="row in myCourses" :key="row.id">
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
              <button class="action-btn action-danger" @click="dropCourse(row)" :disabled="loading">
                退课
              </button>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-else class="muted">暂无已选课程。</p>
      <p class="message" :class="message.ok ? 'ok' : 'error'" v-if="message.text">
        {{ message.text }}
      </p>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { requestJson } from "../api";

const user = ref(null);
const loading = ref(false);
const myCourses = ref([]);
const message = reactive({ text: "", ok: true });

const totalCredits = computed(() =>
  myCourses.value.reduce((sum, row) => sum + Number(row.score || 0), 0)
);

const sno = computed(() => {
  const payload = user.value || {};
  return payload?.userId || payload?.profile?.sno || payload?.profile?.SNO || payload?.sno || "";
});

const normalizeCourses = (rows) =>
  rows.map((row) => ({
    id: row.ID || row.id || row.CNO || row.cno,
    name: row.NAME || row.name || row.CNM || row.cnm,
    time: row.TIME || row.time || row.CTM || row.ctm,
    score: row.SCORE || row.score || row.CPT || row.cpt,
    teacher: row.TEACHER || row.teacher || row.TEC || row.tec,
    location: row.LOCATION || row.location || row.PLA || row.pla,
    share: row.SHARE || row.share,
    grade: row.GRD || row.grd
  }));

const loadMyCourses = async () => {
  if (!sno.value) {
    myCourses.value = [];
    message.ok = false;
    message.text = "请先登录学生账号。";
    return;
  }
  loading.value = true;
  message.text = "";
  try {
    const body = await requestJson(`/api/local/choices?sno=${encodeURIComponent(sno.value)}`);
    myCourses.value = normalizeCourses(body.data || []);
  } catch (err) {
    myCourses.value = [];
    message.ok = false;
    message.text = err?.message || "加载失败";
  } finally {
    loading.value = false;
  }
};

const dropCourse = async (row) => {
  if (!sno.value) return;
  loading.value = true;
  message.text = "";
  try {
    const body = await requestJson("/api/local/choice/drop", {
      method: "POST",
      body: JSON.stringify({ sno: sno.value, cno: row.id })
    });
    message.ok = body.code === 200;
    message.text = body.message || (body.code === 200 ? "退课成功" : "退课失败");
    if (body.code === 200) {
      myCourses.value = myCourses.value.filter((item) => item.id !== row.id);
    }
  } catch (err) {
    message.ok = false;
    message.text = err?.message || "网络错误";
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  const stored = localStorage.getItem("b-user");
  user.value = stored ? JSON.parse(stored) : null;
  loadMyCourses();
});
</script>
