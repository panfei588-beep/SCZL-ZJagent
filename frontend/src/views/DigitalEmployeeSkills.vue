<template>
  <div class="skills-container">
    <el-page-header :icon="null">
      <template #title>
        <span class="page-title">数字员工技能管理 - 质检部</span>
      </template>
    </el-page-header>

    <el-row :gutter="20" class="skills-grid">
      <el-col :span="8">
        <el-card class="skill-card" shadow="hover" @click="goToDiagnosis">
          <div class="card-content">
            <div class="skill-icon">🔍</div>
            <h3 class="skill-title">质量异常诊断</h3>
            <p class="skill-desc">
              基于AI的质量波动根因分析，自动生成改进方案，帮助快速定位质量问题。
            </p>
            <el-button type="primary" class="skill-btn">点击使用 →</el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()

const goToDiagnosis = () => {
  router.push('/tools/quality-diagnosis')
}
</script>

<style scoped>
.skills-container {
  padding: 30px;
  max-width: 1200px;
  margin: 0 auto;
}

.page-title {
  font-size: 22px;
  font-weight: 600;
}

.skills-grid {
  margin-top: 30px;
}

.skill-card {
  cursor: pointer;
  transition: transform 0.3s;
  border-radius: 12px;
}

.skill-card:hover {
  transform: translateY(-4px);
}

.card-content {
  text-align: center;
  padding: 20px 10px;
}

.skill-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.skill-title {
  font-size: 18px;
  margin-bottom: 12px;
  color: #303133;
}

.skill-desc {
  font-size: 14px;
  color: #606266;
  line-height: 1.6;
  margin-bottom: 20px;
}

.skill-btn {
  width: 140px;
}
</style>
