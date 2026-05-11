<template>
  <div class="app-layout">
    <!-- Sidebar -->
    <aside class="sidebar">
      <div class="logo-container">
        <h1 class="logo-title">CorpClaw</h1>
        <p class="logo-subtitle">企业数字员工</p>
      </div>
      
    <nav class="side-nav">
      <div 
        class="nav-item" 
        :class="{ active: route.path === '/tools/quality-diagnosis' }"
        @click="router.push('/tools/quality-diagnosis')"
      >
        <el-icon><Document /></el-icon>
        <span>质量异常诊断专家</span>
      </div>
      <div 
        class="nav-item" 
        :class="{ active: route.path === '/' }"
        @click="router.push('/')"
      >
        <el-icon><Menu /></el-icon>
        <span>数字员工技能管理</span>
      </div>
    </nav>

      <div class="sidebar-footer">
        <div class="nav-item logout">
          <el-icon><SwitchButton /></el-icon>
          <span>退出系统</span>
        </div>
      </div>
    </aside>

    <!-- Main Content -->
    <main class="main-content">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { useRouter, useRoute } from 'vue-router'
import { Document, Menu, SwitchButton } from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
</script>

<style>
.app-layout {
  display: flex;
  height: 100vh;
  width: 100vw;
  overflow: hidden;
  background-color: #f5f7fa;
}

.sidebar {
  width: 240px;
  background-color: #fff;
  border-right: 1px solid var(--border-light);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  z-index: var(--z-nav);
}

.logo-container {
  padding: 24px;
  border-bottom: 1px solid var(--border-light);
}

.logo-title {
  font-size: 20px;
  color: #0045a5;
  font-weight: 800;
  margin: 0;
}

.logo-subtitle {
  font-size: 12px;
  color: #909399;
  margin: 4px 0 0;
}

.side-nav {
  padding: 16px 12px;
  flex: 1;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 6px;
  color: #606266;
  cursor: pointer;
  margin-bottom: 4px;
  transition: all 0.2s;
  font-size: 14px;
}

.nav-item:hover {
  background-color: var(--bg-light);
  color: var(--primary);
}

.nav-item.active {
  background-color: #0052d9;
  color: #fff;
}

.sidebar-footer {
  padding: 16px 12px;
  border-top: 1px solid var(--border-light);
}

.logout {
  color: #606266;
}

.main-content {
  flex: 1;
  overflow-y: auto;
  position: relative;
}

#app {
  margin: 0;
  padding: 0;
  max-width: none;
}
</style>

