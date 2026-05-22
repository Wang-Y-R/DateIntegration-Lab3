<template>
  <section class="view">
    <header class="view-header">
      <div>
        <p class="eyebrow">管理中心</p>
        <h1>学生管理</h1>
      </div>
      <button class="ghost" @click="loadStudents" :disabled="loading">
        {{ loading ? '加载中...' : '刷新数据' }}
      </button>
    </header>

    <div class="card">
      <div class="card-header">
        <h2>学生列表</h2>
        <p>共 {{ students.length }} 名学生。</p>
      </div>
      <table class="data-table">
        <thead>
          <tr>
            <th>学号</th>
            <th>姓名</th>
            <th>性别</th>
            <th>专业</th>
            <th>电话</th>
            <th>邮箱</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="stu in students" :key="stu.sno">
            <td>{{ stu.sno }}</td>
            <td>{{ stu.snm }}</td>
            <td>{{ stu.sex }}</td>
            <td>{{ stu.major }}</td>
            <td>{{ stu.phone || '-' }}</td>
            <td>{{ stu.email || '-' }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<script setup>
import { ref } from "vue";
import { requestJson } from "../api";

const loading = ref(false);
const students = ref([]);

const loadStudents = async () => {
  loading.value = true;
  try {
    const body = await requestJson("/api/local/students?limit=200");
    students.value = body.data || [];
  } catch (err) {
    students.value = [];
  } finally {
    loading.value = false;
  }
};

loadStudents();
</script>