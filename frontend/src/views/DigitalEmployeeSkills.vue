<template>
  <div class="skills-page">
    <!-- Top Tabs Strip -->
    <header class="skills-header">
      <nav class="top-nav">
        <div 
          v-for="tab in tabs" 
          :key="tab" 
          class="top-nav-item" 
          :class="{ active: currentTab === tab }"
          @click="currentTab = tab"
        >
          {{ tab }}
        </div>
      </nav>
    </header>

    <!-- Skills Grid -->
    <div class="skills-grid-container">
      <div class="skills-grid">
        <div 
          v-for="skill in filteredSkills" 
          :key="skill.id" 
          class="skill-card-v2 card"
          @click="handleSkillClick(skill)"
        >
          <div class="card-top">
            <div class="icon-box" :style="{ backgroundColor: skill.bgColor }">
              <el-icon :size="24"><component :is="skill.iconComponent" /></el-icon>
            </div>
            <el-icon class="cloud-icon" color="#C0C4CC"><Cloudy /></el-icon>
          </div>
          
          <div class="skill-info">
            <h3 class="skill-title-v2">{{ skill.title }}</h3>
            <p class="skill-desc-v2">{{ skill.desc }}</p>
          </div>

          <div class="skill-footer">
            <span class="use-link">点击使用 <el-icon><ArrowRight /></el-icon></span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, markRaw } from 'vue'
import { useRouter } from 'vue-router'
import { 
  DataAnalysis, Document, List, Search, Files, Connection, 
  EditPen, Setting, Postcard, CircleCheck, Reading, ArrowRight,
  Cloudy
} from '@element-plus/icons-vue'

const router = useRouter()
const currentTab = ref('部门技能')
const tabs = ['部门技能', '生产部', '质检部', '工艺部', '设备部', '技术部', '管理部', '后勤部', '通用工具']

const allSkills = [
  { id: 1, title: '生产质量数字专家', desc: '基于质检实测数据分析，自动生成可视化数据报告和改进方案，帮助快速定位质量问题。', iconComponent: markRaw(Document), bgColor: '#E6F4FF', route: '/tools/quality-diagnosis' },
]

const filteredSkills = computed(() => {
  if (currentTab.value === '部门技能') return allSkills
  return allSkills.slice(0, 5)
})

const handleSkillClick = (skill) => {
  if (skill.route) {
    router.push(skill.route)
  }
}
</script>

<style scoped>
.skills-page {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.skills-header {
  background-color: #fff;
  border-bottom: 1px solid var(--border-light);
  padding: 0 40px;
  position: sticky;
  top: 0;
  z-index: 10;
}

.top-nav {
  display: flex;
  height: 64px;
}

.top-nav-item {
  display: flex;
  align-items: center;
  padding: 0 20px;
  font-size: 14px;
  color: #606266;
  cursor: pointer;
  position: relative;
  transition: color 0.2s;
}

.top-nav-item:hover {
  color: var(--primary);
}

.top-nav-item.active {
  color: var(--primary);
  font-weight: 600;
}

.top-nav-item.active::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 20px;
  right: 20px;
  height: 3px;
  background-color: var(--primary);
  border-radius: 3px 3px 0 0;
}

.skills-grid-container {
  padding: 40px;
  flex: 1;
}

.skills-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 24px;
  max-width: 1600px;
  margin: 0 auto;
}

.skill-card-v2 {
  padding: 24px;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  height: 220px;
  justify-content: space-between;
}

.card-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.icon-box {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #409eff;
}

.skill-info {
  margin-top: 16px;
  flex: 1;
}

.skill-title-v2 {
  font-size: 16px;
  color: #303133;
  margin: 0 0 8px;
  font-weight: 600;
}

.skill-desc-v2 {
  font-size: 13px;
  color: #909399;
  line-height: 1.5;
  margin: 0;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.skill-footer {
  display: flex;
  justify-content: flex-end;
}

.use-link {
  font-size: 13px;
  color: var(--primary);
  display: flex;
  align-items: center;
  gap: 4px;
  transition: transform 0.2s;
}

.skill-card-v2:hover .use-link {
  transform: translateX(4px);
}
</style>

