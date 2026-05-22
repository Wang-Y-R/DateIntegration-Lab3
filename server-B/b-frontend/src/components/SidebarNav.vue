<template>
  <aside class="sidebar">
    <div class="sidebar-header">
      <div class="brand-mark" aria-hidden="true">
        <svg viewBox="0 0 48 48" role="img" aria-label="B院系">
          <path d="M24 6l16 6v11c0 10.5-7.6 18.2-16 19-8.4-.8-16-8.5-16-19V12l16-6z" fill="currentColor" opacity="0.15"/>
          <path d="M24 6l16 6v11c0 10.5-7.6 18.2-16 19-8.4-.8-16-8.5-16-19V12l16-6z" fill="none" stroke="currentColor" stroke-width="2.2"/>
          <path d="M18 18h10a5 5 0 0 1 0 10H18z" fill="none" stroke="currentColor" stroke-width="2"/>
          <path d="M18 18v12" fill="none" stroke="currentColor" stroke-width="2"/>
          <text x="24" y="30" text-anchor="middle" font-size="14" font-weight="700" fill="currentColor">B</text>
        </svg>
      </div>
      <div>
        <p class="brand-title">B院选课系统</p>
        <p class="brand-sub">教务服务门户</p>
      </div>
    </div>

    <div class="sidebar-links">
      <RouterLink to="/login" class="sidebar-link">
        <span class="icon">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M6 10V7a6 6 0 1 1 12 0v3" fill="none" stroke="currentColor" stroke-width="1.8"/>
            <rect x="4" y="10" width="16" height="10" rx="2.5" fill="none" stroke="currentColor" stroke-width="1.8"/>
            <circle cx="12" cy="15" r="1.5" fill="currentColor"/>
          </svg>
        </span>
        <span>登录入口</span>
      </RouterLink>

      <template v-if="!isAdmin">
        <RouterLink to="/profile" class="sidebar-link">
          <span class="icon">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <circle cx="12" cy="8" r="4" fill="none" stroke="currentColor" stroke-width="1.8"/>
              <path d="M4 20c1.6-3.8 5-6 8-6s6.4 2.2 8 6" fill="none" stroke="currentColor" stroke-width="1.8"/>
            </svg>
          </span>
          <span>个人信息</span>
        </RouterLink>
        <RouterLink to="/choice" class="sidebar-link">
          <span class="icon">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M4 7h12" fill="none" stroke="currentColor" stroke-width="1.8"/>
              <path d="M4 12h10" fill="none" stroke="currentColor" stroke-width="1.8"/>
              <path d="M4 17h8" fill="none" stroke="currentColor" stroke-width="1.8"/>
              <path d="M18 7l2 2-6 6-3 1 1-3 6-6z" fill="none" stroke="currentColor" stroke-width="1.6"/>
            </svg>
          </span>
          <span>我的课程</span>
        </RouterLink>
        <RouterLink to="/courses" class="sidebar-link">
          <span class="icon">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M5 5h11a3 3 0 0 1 3 3v11H8a3 3 0 0 0-3 3V5z" fill="none" stroke="currentColor" stroke-width="1.8"/>
              <path d="M5 19V5" fill="none" stroke="currentColor" stroke-width="1.8"/>
            </svg>
          </span>
          <span>课程列表</span>
        </RouterLink>
      </template>

      
      <template v-if="isAdmin">
        <RouterLink to="/courses" class="sidebar-link">
          <span class="icon">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M5 5h11a3 3 0 0 1 3 3v11H8a3 3 0 0 0-3 3V5z" fill="none" stroke="currentColor" stroke-width="1.8"/>
              <path d="M5 19V5" fill="none" stroke="currentColor" stroke-width="1.8"/>
            </svg>
          </span>
          <span>课程列表</span>
        </RouterLink>
        </template>


        <RouterLink to="/cross-choice" class="sidebar-link">
          <span class="icon">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M4 12h6" fill="none" stroke="currentColor" stroke-width="1.8"/>
              <path d="M14 12h6" fill="none" stroke="currentColor" stroke-width="1.8"/>
              <path d="M10 8l-4 4 4 4" fill="none" stroke="currentColor" stroke-width="1.8"/>
              <path d="M14 8l4 4-4 4" fill="none" stroke="currentColor" stroke-width="1.8"/>
            </svg>
          </span>
        <span>跨系选课</span>
      </RouterLink>
      <RouterLink to="/stats" class="sidebar-link">
        <span class="icon">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M5 19V9" fill="none" stroke="currentColor" stroke-width="1.8"/>
            <path d="M12 19V5" fill="none" stroke="currentColor" stroke-width="1.8"/>
            <path d="M19 19V12" fill="none" stroke="currentColor" stroke-width="1.8"/>
          </svg>
        </span>
        <span>统计概览</span>
      </RouterLink>
    </div>

    <div class="sidebar-footer">
      <p>服务状态：正常</p>
    </div>
  </aside>
</template>

<script setup>
import { RouterLink } from "vue-router";
import { computed } from "vue";

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
</script>
