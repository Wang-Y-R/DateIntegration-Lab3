<template>
  <section class="view">
    <header class="view-header">
      <div>
        <p class="eyebrow">管理中心</p>
        <h1>课程管理</h1>
      </div>
      <button class="primary" @click="showAddForm = !showAddForm">
        {{ showAddForm ? '取消添加' : '新增课程' }}
      </button>
    </header>

    <div class="card" v-if="showAddForm">
      <div class="card-header">
        <h2>新增课程</h2>
      </div>
      <form class="form-grid" @submit.prevent="handleAddCourse">
        <label>
          课程编号
          <input v-model="courseForm.cno" placeholder="如：C01" required />
        </label>
        <label>
          课程名称
          <input v-model="courseForm.cnm" placeholder="课程名称" required />
        </label>
        <label>
          时间段
          <select v-model="courseForm.ctm" required>
            <option value="1">周一第1-2节</option>
            <option value="2">周一第3-4节</option>
            <option value="3">周二第1-2节</option>
            <option value="4">周二第3-4节</option>
            <option value="5">周三第1-2节</option>
            <option value="6">周三第3-4节</option>
          </select>
        </label>
        <label>
          课程性质
          <select v-model="courseForm.cpt" required>
            <option value="1">必修</option>
            <option value="2">选修</option>
          </select>
        </label>
        <label>
          授课教师
          <input v-model="courseForm.tec" placeholder="教师姓名" required />
        </label>
        <label>
          上课地点
          <input v-model="courseForm.pla" placeholder="教室位置" required />
        </label>
        <button class="primary" type="submit" :disabled="adding">
          {{ adding ? '添加中...' : '确认添加' }}
        </button>
      </form>
      <p class="message" :class="addMessage.ok ? 'ok' : 'error'" v-if="addMessage.text">
        {{ addMessage.text }}
      </p>
    </div>

    <div class="card">
      <div class="card-header">
        <h2>课程列表</h2>
        <p>共 {{ courses.length }} 门课程。</p>
      </div>
      <table class="data-table">
        <thead>
          <tr>
            <th>课程编号</th>
            <th>课程名称</th>
            <th>时间段</th>
            <th>性质</th>
            <th>教师</th>
            <th>地点</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="course in courses" :key="course.cno">
            <td>{{ course.cno }}</td>
            <td>{{ course.cnm }}</td>
            <td>{{ course.ctm }}</td>
            <td>{{ course.cpt === '1' ? '必修' : '选修' }}</td>
            <td>{{ course.tec }}</td>
            <td>{{ course.pla }}</td>
            <td>
              <button class="ghost" @click="handleDeleteCourse(course.cno)" :disabled="deleting">
                删除
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<script setup>
import { reactive, ref } from "vue";
import { requestJson } from "../api";

const loading = ref(false);
const adding = ref(false);
const deleting = ref(false);
const showAddForm = ref(false);
const courses = ref([]);

const courseForm = reactive({
  cno: "",
  cnm: "",
  ctm: "1",
  cpt: "1",
  tec: "",
  pla: ""
});

const addMessage = reactive({ text: "", ok: true });

const loadCourses = async () => {
  loading.value = true;
  try {
    const body = await requestJson("/api/local/courses");
    courses.value = body.data || [];
  } catch (err) {
    courses.value = [];
  } finally {
    loading.value = false;
  }
};

const handleAddCourse = async () => {
  adding.value = true;
  addMessage.text = "";
  try {
    const body = await requestJson("/api/admin/course/add", {
      method: "POST",
      body: JSON.stringify(courseForm)
    });
    if (body.code !== 200) {
      addMessage.ok = false;
      addMessage.text = body.message || "添加失败";
      return;
    }
    addMessage.ok = true;
    addMessage.text = body.message || "添加成功";
    courseForm.cno = "";
    courseForm.cnm = "";
    courseForm.tec = "";
    courseForm.pla = "";
    await loadCourses();
  } catch (err) {
    addMessage.ok = false;
    addMessage.text = err?.message || "网络错误";
  } finally {
    adding.value = false;
  }
};

const handleDeleteCourse = async (cno) => {
  if (!confirm(`确定要删除课程 ${cno} 吗？`)) return;
  deleting.value = true;
  try {
    const body = await requestJson(`/api/admin/course/delete?cno=${cno}`, {
      method: "POST"
    });
    if (body.code !== 200) {
      alert(body.message || "删除失败");
      return;
    }
    await loadCourses();
  } catch (err) {
    alert(err?.message || "网络错误");
  } finally {
    deleting.value = false;
  }
};

loadCourses();
</script>