<template>
  <section class="view">
    <header class="view-header">
      <div>
        <p class="eyebrow">统计中心</p>
        <h1>统计概览</h1>
      </div>
      <button class="ghost" @click="loadStats" :disabled="loading">
        {{ loading ? '加载中...' : '刷新数据' }}
      </button>
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

    <div class="card" v-if="isAdmin && detailedStats">
      <div class="card-header">
        <h2>详细统计 - 学生选课明细</h2>
        <p>每位学生的选课数量统计。</p>
      </div>
      <table class="data-table">
        <thead>
          <tr>
            <th>学号</th>
            <th>姓名</th>
            <th>专业</th>
            <th>选课数量</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in detailedStats" :key="row.sno">
            <td>{{ row.sno }}</td>
            <td>{{ row.snm }}</td>
            <td>{{ row.major }}</td>
            <td>{{ row.choiceCount }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="card" v-if="courseChoiceList.length">
      <div class="card-header">
        <h2>课程被选次数</h2>
        <p>按课程编号汇总。</p>
      </div>
      <table class="data-table">
        <thead>
          <tr>
            <th>课程编号</th>
            <th>课程名称</th>
            <th>选课次数</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in courseChoiceList" :key="row.cno">
            <td>{{ row.cno }}</td>
            <td>{{ row.cnm }}</td>
            <td>{{ row.count }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <p v-if="!stats && !isAdmin" class="muted">暂无统计数据。</p>
  </section>
</template>

<script setup>
import { computed, ref } from "vue";
import { requestJson } from "../api";

const loading = ref(false);
const stats = ref(null);
const detailedStats = ref(null);

const isAdmin = computed(() => {
  const user = localStorage.getItem("b-user");
  if (!user) return false;
  try {
    const userData = JSON.parse(user);
    return userData.role === "ADMIN";
  } catch {
    return false;
  }
});

const courseChoiceList = computed(() => {
  const raw = stats.value?.courseChoiceCounts || {};
  const courseNames = stats.value?.courseNames || {};
  return Object.entries(raw).map(([cno, count]) => ({ 
    cno, 
    count, 
    cnm: courseNames[cno] || '-' 
  }));
});

const loadStats = async () => {
  loading.value = true;
  try {
    const body = await requestJson("/api/local/stats/overview");
    stats.value = body.data || null;
    
    if (isAdmin.value) {
      const detailBody = await requestJson("/api/admin/stats/detailed");
      detailedStats.value = detailBody.data || [];
    } else {
      detailedStats.value = null;
    }
  } catch (err) {
    stats.value = null;
    detailedStats.value = null;
  } finally {
    loading.value = false;
  }
};

loadStats();
</script>