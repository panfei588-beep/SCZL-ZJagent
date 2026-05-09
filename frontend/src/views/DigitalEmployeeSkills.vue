<template>
  <div class="skills-container">
    <div class="skills-panel">
      <div class="panel-header">
        <el-icon class="header-icon"><Tools /></el-icon>
        数字员工技能管理 - 质检部
      </div>
      <div class="panel-body">
        <el-card class="skill-card" shadow="hover" @click="goToDiagnosis">
          <div class="card-content">
            <el-icon class="skill-icon" :size="56"><DataAnalysis /></el-icon>
            <h3 class="skill-title">质量异常诊断</h3>
            <p class="skill-desc">
              基于AI的质量波动根因分析，自动生成改进方案，帮助快速定位质量问题。
            </p>
            <el-button type="primary" class="skill-btn">
              <span>点击使用</span>
              <el-icon class="arrow-icon"><ArrowRight /></el-icon>
            </el-button>
          </div>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { Tools, DataAnalysis, ArrowRight } from '@element-plus/icons-vue'

const router = useRouter()

const goToDiagnosis = () => {
  router.push('/tools/quality-diagnosis')
}
</script>

<style scoped>
.skills-container {
  height: 100vh;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 50px;
  background: var(--bg-page);
}

.skills-panel {
  width: 100%;
  max-width: 1000px;
  background: var(--bg-white);
  border-radius: var(--radius);
  box-shadow: var(--shadow-base);
  overflow: hidden;
}

.panel-header {
  font-size: 16px;
  font-weight: 600;
  padding: 14px 24px;
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--bg-light);
  border-bottom: 1px solid var(--border-light);
  color: var(--text-primary);
}

.header-icon {
  font-size: 20px;
  color: var(--primary);
}

.panel-body {
  padding: 40px 24px;
  display: flex;
  justify-content: center;
}

.skill-card {
  cursor: pointer;
  transition: transform 0.3s, box-shadow 0.3s;
  border-radius: var(--radius-lg);
  width: 300px;
}

.skill-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-hover);
}

.card-content {
  text-align: center;
  padding: 24px 12px;
}

.skill-icon {
  color: var(--primary);
  margin-bottom: 16px;
}

.skill-title {
  font-size: 18px;
  margin-bottom: 12px;
  color: var(--text-primary);
}

.skill-desc {
  font-size: 14px;
  color: var(--text-regular);
  line-height: 1.6;
  margin-bottom: 20px;
}

.skill-btn .arrow-icon {
  margin-left: 4px;
}
</style>
