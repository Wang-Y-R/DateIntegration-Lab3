<template>
  <div class="app">
    <div class="layout">
      <SidebarNav />
      <main class="content">
        <Transition name="fade" mode="out-in">
          <RouterView />
        </Transition>
      </main>
    </div>
  </div>
</template>

<script setup>
import { RouterView } from "vue-router";
import SidebarNav from "./components/SidebarNav.vue";
</script>
