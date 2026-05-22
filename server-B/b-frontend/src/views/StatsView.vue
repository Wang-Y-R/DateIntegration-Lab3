<template>
  <section class="view">
    <header class="view-header">
      <div>
        <p class="eyebrow">统计中心</p>
        <h1>统计概览</h1>
      </div>
      <div class="header-actions">
        <button class="ghost" @click="loadStats" :disabled="loading">
          {{ loading ? '加载中...' : '刷新数据' }}
        </button>
      </div>
    </header>

    <div class="stats" v-if="stats">
      <div class="stat">
        <span>学生总数</span>
        <strong>{{ stats.studentCount ?? '-' }}</strong>
      </div>
      <div class="stat">
        <span>课程总数</span>
        <strong>{{ stats.courseCount ?? '-' }}</strong>
      </div>
      <div class="stat">
        <span>选课记录</span>
        <strong>{{ stats.choiceCount ?? '-' }}</strong>
      </div>
    </div>

    <div class="card" v-if="topCourses.length">
      <div class="card-header">
        <h2>Top 热门课程</h2>
      </div>
      <ul class="top-list">
        <li v-for="c in topCourses" :key="c.cno" class="top-item">
          <div class="top-meta">
            <strong class="cno">{{ c.cno }}</strong>
            <span class="cnm">{{ c.cnm }}</span>
            <span class="count">{{ c.count }}</span>
          </div>
          <div class="bar-wrap">
            <div class="bar" :style="{ width: (c.count / maxCount * 100) + '%' }"></div>
          </div>
        </li>
      </ul>
    </div>

    <div class="card" v-if="courseChoiceList.length">
      <div class="card-header">
        <h2>课程被选次数</h2>
      </div>
      <table class="data-table">
        <thead>
          <tr>
            <th @click="sortBy('cno')">课程编号</th>
            <th @click="sortBy('cnm')">课程名称</th>
            <th @click="sortBy('count')">选课次数</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in sortedCourseChoiceList" :key="row.cno">
            <td>{{ row.cno }}</td>
            <td>{{ row.cnm }}</td>
            <td>{{ row.count }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="card" v-if="studentChoiceList.length">
      <div class="card-header">
        <h2>学生选课分布</h2>
      </div>
      <table class="data-table">
        <thead>
          <tr>
            <th>学号</th>
            <th>姓名</th>
            <th>选课数量</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="s in studentChoiceList" :key="s.sno">
            <td>{{ s.sno }}</td>
            <td>{{ s.snm || '-' }}</td>
            <td>{{ s.choiceCount }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <p v-if="!stats" class="muted">暂无统计数据。</p>
  </section>
</template>

<script setup>
import { computed, ref } from "vue";
import { requestJson } from "../api";

const loading = ref(false);
const stats = ref(null);
const sortKey = ref('count');
const sortDir = ref('desc');

const loadStats = async () => {
  loading.value = true;
  try {
    const body = await requestJson("/api/local/stats/overview");
    stats.value = body.data || null;
  } catch (err) {
    stats.value = null;
  } finally {
    loading.value = false;
  }
};

const courseChoiceList = computed(() => {
  const raw = stats.value?.courseChoiceCounts || {};
  const courseNames = stats.value?.courseNames || {};
  return Object.entries(raw).map(([cno, count]) => ({
    cno,
    count,
    cnm: courseNames[cno] || '-'
  }));
});

const maxCount = computed(() => {
  const list = courseChoiceList.value;
  if (!list.length) return 1;
  return Math.max(...list.map(i => i.count)) || 1;
});

const topCourses = computed(() => {
  return [...courseChoiceList.value].sort((a, b) => b.count - a.count).slice(0, 5);
});

const sortedCourseChoiceList = computed(() => {
  const list = [...courseChoiceList.value];
  const key = sortKey.value;
  const dir = sortDir.value === 'desc' ? -1 : 1;
  list.sort((a, b) => {
    if (a[key] == null) return 1;
    if (b[key] == null) return -1;
    if (typeof a[key] === 'number') return (a[key] - b[key]) * dir;
    return a[key].localeCompare(b[key]) * dir;
  });
  return list;
});

const studentChoiceList = computed(() => {
  if (Array.isArray(stats.value?.studentChoiceList)) {
    return stats.value.studentChoiceList;
  }
  const obj = stats.value?.studentChoiceCounts || {};
  if (Object.keys(obj || {}).length === 0) return [];
  const names = stats.value?.studentNames || {};
  return Object.entries(obj).map(([sno, choiceCount]) => ({
    sno,
    snm: names[sno] || '',
    choiceCount
  })).sort((a,b) => b.choiceCount - a.choiceCount);
});

const sortBy = (k) => {
  if (sortKey.value === k) {
    sortDir.value = sortDir.value === 'desc' ? 'asc' : 'desc';
  } else {
    sortKey.value = k;
    sortDir.value = 'desc';
  }
};

loadStats();
</script>

<style scoped>
.header-actions { display:flex; gap:8px; align-items:center; }
.top-list { list-style: none; margin:0; padding:0;}
.top-item { padding:10px 0; border-bottom:1px solid #eee; }
.top-meta { display:flex; gap:8px; align-items:center; margin-bottom:6px; }
.top-meta .cno { width:72px; display:inline-block; }
.top-meta .cnm { flex:1; color:#333; }
.top-meta .count { width:64px; text-align:right; font-weight:600; }
.bar-wrap { height:8px; background:#f1f1f1; border-radius:4px; overflow:hidden; }
.bar { height:100%; background:linear-gradient(90deg,#4f9ef5,#2b7be2); }
.data-table th { cursor: pointer; user-select:none; }
</style>