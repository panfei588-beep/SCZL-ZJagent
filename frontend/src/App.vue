<template>
  <div class="app-layout">
    <!-- Sidebar -->
    <aside class="sidebar">
      <div class="logo-container">
        <img src="https://cdn.phototourl.com/free/2026-05-19-317de74c-4617-4c56-8c3d-f34fcb0d1f2a.png" alt="航天爱锐" class="logo-image">
        <p class="logo-subtitle">企业数字员工</p>
      </div>
      
    <nav class="side-nav">
      <div 
        class="nav-item" 
        :class="{ active: route.path === '/tools/quality-diagnosis' }"
        @click="router.push('/tools/quality-diagnosis')"
      >
        <el-icon><Document /></el-icon>
        <span>质量改善管理专家</span>
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
  padding: 20px;
  box-sizing: border-box;
}

.logo-container {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: -2px;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid #f0f0f0;
  padding-top: 10px;
}

.logo-image {
  height: 65px;
  width: auto;
  display: block;
  object-fit: contain;
}

.logo-subtitle {
  font-size: 16px;
  color: #606266;
  font-weight: 500;
  margin: 0;
  letter-spacing: 0.5px;
}

.side-nav {
  display: flex;
  flex-direction: column;
  flex: 1;
  gap: 8px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 8px;
  color: #606266;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 14px;
  text-align: left;
}

.nav-item:hover {
  background-color: #f0f4ff;
  color: #0052d9;
}

.nav-item.active {
  background-color: #0052d9;
  color: #fff;
}

.sidebar-footer {
  margin-top: 20px;
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

