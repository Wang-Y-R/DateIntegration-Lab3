<template>
  <section class="view">
    <header class="view-header">
      <div>
        <p class="eyebrow">登录中心</p>
        <h1>院系选课登录</h1>
      </div>
      <div class="status-pill" :class="user ? 'on' : 'off'">
        <span class="dot"></span>
        <span>{{ user ? '已登录' : '未登录' }}</span>
      </div>
    </header>

    <div class="card login-card">
      <div class="card-header">
        <h2>账号登录</h2>
        <p>支持学生与管理员账号。</p>
      </div>
      <form class="form-grid" @submit.prevent="handleLogin">
        <label>
          身份类型
          <select v-model="loginForm.type">
            <option value="STUDENT">学生</option>
            <option value="ADMIN">管理员</option>
          </select>
        </label>
        <label>
          账号
          <input v-model="loginForm.username" placeholder="B2023001" />
        </label>
        <label>
          密码
          <input v-model="loginForm.password" type="password" placeholder="请输入密码" />
        </label>
        <button class="primary" type="submit" :disabled="loading">
          {{ loading ? '登录中...' : '登录' }}
        </button>
      </form>
      <p class="message" :class="authMessage.ok ? 'ok' : 'error'" v-if="authMessage.text">
        {{ authMessage.text }}
      </p>
      <div class="user-box" v-if="user">
        <h3>登录信息</h3>
        <p>登录成功，欢迎回来。</p>
        <button class="ghost" type="button" @click="handleLogout">退出登录</button>
      </div>
    </div>
  </section>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue";
import { requestJson } from "../api";

const loginForm = reactive({
  type: "STUDENT",
  username: "",
  password: ""
});

const loading = ref(false);
const user = ref(null);
const authMessage = reactive({ text: "", ok: true });

const loadStoredUser = () => {
  const stored = localStorage.getItem("b-user");
  user.value = stored ? JSON.parse(stored) : null;
};

const handleLogin = async () => {
  loading.value = true;
  authMessage.text = "";
  try {
    const payload = {
      type: loginForm.type,
      username: (loginForm.username || "").trim(),
      password: (loginForm.password || "").trim()
    };
    if (!payload.username || !payload.password) {
      authMessage.ok = false;
      authMessage.text = "请输入账号和密码。";
      return;
    }
    const body = await requestJson("/api/auth/login", {
      method: "POST",
      body: JSON.stringify(payload)
    });
    if (body.code !== 200) {
      authMessage.ok = false;
      authMessage.text = body.message || "登录失败";
      user.value = null;
      return;
    }
    authMessage.ok = true;
    authMessage.text = body.message || "登录成功";
    user.value = body.data;
    localStorage.setItem("b-user", JSON.stringify(body.data || {}));

    const profile = body?.data?.profile;
    if (profile && (profile.sno || profile.snm)) {
      const profilePayload = {
        sno: profile.sno || "",
        name: profile.snm || "",
        sex: profile.sex || "男",
        major: profile.major || "",
        origin: profile.origin || ""
      };
      localStorage.setItem("b-profile", JSON.stringify(profilePayload));
    }
  } catch (err) {
    authMessage.ok = false;
    authMessage.text = err?.message || "网络错误";
  } finally {
    loading.value = false;
  }
};

const handleLogout = () => {
  localStorage.removeItem("b-user");
  user.value = null;
  authMessage.ok = true;
  authMessage.text = "已退出登录。";
};

onMounted(() => {
  loadStoredUser();
});
</script>
