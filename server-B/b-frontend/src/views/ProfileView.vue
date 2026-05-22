<template>
  <section class="view">
    <header class="view-header">
      <div>
        <p class="eyebrow">学生中心</p>
        <h1>个人信息</h1>
        <p class="subtitle">请完善个人信息，便于后续选课与通知。</p>
      </div>
    </header>

    <div class="card">
      <div class="card-header">
        <h2>基本信息</h2>
      </div>
      <form class="form-columns" @submit.prevent>
        <label>
          学号
          <input v-model="profile.sno" placeholder="B2023001" readonly />
        </label>
        <label>
          姓名
          <input v-model="profile.name" placeholder="张三" readonly />
        </label>
        <label>
          性别
          <select v-model="profile.sex" disabled>
            <option value="男">男</option>
            <option value="女">女</option>
          </select>
        </label>
        <label>
          专业
          <input v-model="profile.major" placeholder="软件工程" readonly />
        </label>
        <div class="form-row">
          <label>
            手机
            <input v-model="profile.phone" placeholder="13800000000" />
          </label>
          <label>
            邮箱
            <input v-model="profile.email" placeholder="student@campus.edu" />
          </label>
        </div>
      </form>
      <div class="button-row">
        <button class="primary" @click="saveProfile">保存信息</button>
        <button class="ghost" @click="resetProfile">恢复默认</button>
      </div>
      <p class="message" :class="message.ok ? 'ok' : 'error'" v-if="message.text">
        {{ message.text }}
      </p>
    </div>
  </section>
</template>

<script setup>
import { onMounted, reactive } from "vue";
import { requestJson } from "../api";

const storedUser = localStorage.getItem("b-user");
const userPayload = storedUser ? JSON.parse(storedUser) : {};
const userProfile = userPayload?.profile || userPayload || {};

const profile = reactive({
  sno: userProfile?.sno || userProfile?.SNO || "",
  name: userProfile?.snm || userProfile?.name || userProfile?.NAME || "",
  sex: userProfile?.sex || "男",
  major: userProfile?.major || "",
  phone: "",
  email: ""
});

const message = reactive({ text: "", ok: true });

const loadProfile = async () => {
  if (!profile.sno) {
    message.ok = false;
    message.text = "请先登录学生账号。";
    return;
  }
  try {
    const body = await requestJson(`/api/local/students/profile?sno=${encodeURIComponent(profile.sno)}`);
    const data = body.data || {};
    Object.assign(profile, {
      sno: data.sno || profile.sno,
      name: data.snm || profile.name,
      sex: data.sex || profile.sex,
      major: data.major || profile.major,
      phone: data.phone || "",
      email: data.email || ""
    });
    message.text = "";
  } catch (err) {
    message.ok = false;
    message.text = err?.message || "个人信息加载失败";
  }
};

const saveProfile = async () => {
  if (!profile.sno) {
    message.ok = false;
    message.text = "请先登录学生账号。";
    return;
  }
  try {
    const body = await requestJson("/api/local/students/profile", {
      method: "POST",
      body: JSON.stringify({
        sno: profile.sno,
        phone: profile.phone,
        email: profile.email
      })
    });
    if (body.code !== 200) {
      message.ok = false;
      message.text = body.message || "保存失败";
      return;
    }
    const data = body.data || {};
    Object.assign(profile, {
      phone: data.phone || "",
      email: data.email || ""
    });
    message.ok = true;
    message.text = body.message || "保存成功。";
  } catch (err) {
    message.ok = false;
    message.text = err?.message || "网络错误";
  }
};

const resetProfile = async () => {
  await loadProfile();
  if (!message.text) {
    message.ok = true;
    message.text = "已恢复最新信息。";
  }
};

onMounted(() => {
  loadProfile();
});
</script>
