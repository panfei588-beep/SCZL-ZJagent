<template>
  <div class="workbench">
    <el-page-header @back="goBack" content="质量异常诊断工作台" />

    <el-steps :active="currentStep" align-center class="steps">
      <el-step title="上传数据" :icon="Upload" />
      <el-step title="AI诊断" :icon="Loading" />
      <el-step title="查看结果" :icon="Document" />
      <el-step title="改进方案" :icon="Check" />
    </el-steps>

    <!-- 步骤1：上传数据 -->
    <el-card v-show="currentStep === 0" class="step-card">
      <template #header><span>步骤1：上传质量数据</span></template>

      <el-upload
        drag
        :auto-upload="false"
        :on-change="handleFileChange"
        accept=".xlsx,.xls,.pdf,.jpg,.png,.docx"
        :limit="1"
      >
        <el-icon class="el-icon--upload" :size="40"><UploadFilled /></el-icon>
        <div class="el-upload__text">拖拽文件到此处或<em>点击上传</em></div>
        <template #tip>
          <div class="el-upload__tip">支持Excel、PDF、图片、Word格式，单个文件不超过50MB</div>
        </template>
      </el-upload>

      <!-- 分析范围选择 -->
      <el-form :model="analysisParams" label-width="100px" class="params-form">
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="设备">
              <el-select v-model="analysisParams.equipment" placeholder="选择设备">
                <el-option label="3号精密磨床" value="3号精密磨床" />
                <el-option label="2号外圆磨床" value="2号外圆磨床" />
                <el-option label="5号内圆磨床" value="5号内圆磨床" />
                <el-option label="CNC车床-05" value="CNC车床-05" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="时间范围">
              <el-select v-model="analysisParams.days" placeholder="选择时间">
                <el-option label="最近3天" :value="3" />
                <el-option label="最近7天" :value="7" />
                <el-option label="最近14天" :value="14" />
                <el-option label="最近30天" :value="30" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="操作员">
              <el-select v-model="analysisParams.operator" placeholder="全部" clearable>
                <el-option label="张伟" value="张伟" />
                <el-option label="李四" value="李四" />
                <el-option label="王强" value="王强" />
                <el-option label="赵明" value="赵明" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>

      <!-- 数据预览 -->
      <div v-if="uploadedData.length > 0" class="data-preview">
        <h4>数据预览（前5条）</h4>
        <el-table :data="uploadedData.slice(0, 5)" border stripe>
          <el-table-column prop="日期" label="日期" width="110" />
          <el-table-column prop="产品编号" label="产品编号" width="110" />
          <el-table-column prop="检测项" label="检测项" width="80" />
          <el-table-column prop="标准值" label="标准值" width="120" />
          <el-table-column prop="实测值" label="实测值" width="100" />
          <el-table-column prop="判定" label="判定" width="80">
            <template #default="scope">
              <el-tag :type="scope.row['判定'] === '合格' ? 'success' : 'danger'" size="small">
                {{ scope.row['判定'] }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="操作员" label="操作员" width="80" />
        </el-table>

        <div class="upload-info">
          <el-alert :title="`文件上传成功！已识别 ${totalRecords} 条质量记录`" type="success" show-icon :closable="false" />
        </div>

        <el-button type="primary" size="large" @click="startDiagnosis" class="next-btn">
          开始AI诊断 →
        </el-button>
      </div>
    </el-card>

    <!-- 步骤2：AI诊断中 -->
    <el-card v-show="currentStep === 1" class="step-card">
      <template #header><span>步骤2：AI诊断分析</span></template>
      <div class="diagnosis-loading">
        <el-icon class="is-loading" :size="50" color="#409EFF"><Loading /></el-icon>
        <h3>AI正在分析中，请稍候...</h3>
        <el-progress :percentage="diagnosisProgress" style="max-width:500px;margin:20px auto" />
        <div class="progress-steps">
          <div v-for="(step, idx) in progressSteps" :key="idx" class="progress-step">
            <el-icon v-if="step.done" color="#67C23A"><CircleCheck /></el-icon>
            <el-icon v-else-if="step.current" class="is-loading" color="#409EFF"><Loading /></el-icon>
            <el-icon v-else color="#DCDFE6"><Clock /></el-icon>
            <span :style="{ color: step.done ? '#67C23A' : step.current ? '#409EFF' : '#909399' }">
              {{ step.text }}
            </span>
          </div>
        </div>
      </div>
    </el-card>

    <!-- 步骤3：诊断结果 -->
    <el-card v-show="currentStep === 2" class="step-card">
      <template #header><span>步骤3：诊断结果</span></template>

      <el-alert title="✅ AI诊断完成！" type="success" :closable="false" show-icon style="margin-bottom:20px" />

      <!-- 质量趋势图 -->
      <div class="trend-section">
        <h4>质量趋势分析</h4>
        <div ref="trendChartRef" style="width:100%;height:320px"></div>
      </div>

      <!-- 根因诊断结果 -->
      <div v-if="diagnosisResult?.root_causes?.length">
        <h4 class="section-title">根因诊断结果</h4>
        <el-card
          v-for="cause in diagnosisResult.root_causes"
          :key="cause.rank"
          class="cause-card"
          shadow="hover"
        >
          <div class="cause-header">
            <el-tag size="large" type="danger">根因{{ cause.rank }}</el-tag>
            <h4 style="margin:0">{{ cause.cause }}</h4>
          </div>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="类别">
              <el-tag>{{ cause.category }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="置信度">
              <el-progress
                :percentage="Math.round(cause.confidence * 100)"
                :color="cause.confidence > 0.8 ? '#67C23A' : '#E6A23C'"
                style="width:160px"
              />
            </el-descriptions-item>
            <el-descriptions-item label="证据" :span="2">
              <ul style="margin:0;padding-left:20px">
                <li v-for="(ev, i) in cause.evidence" :key="i">{{ ev }}</li>
              </ul>
            </el-descriptions-item>
            <el-descriptions-item label="影响" :span="2">{{ cause.impact }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </div>

      <!-- 相似案例 -->
      <div v-if="diagnosisResult?.similar_cases?.length">
        <h4 class="section-title">相似历史案例</h4>
        <el-table :data="diagnosisResult.similar_cases" border stripe>
          <el-table-column prop="case_id" label="案例编号" width="110" />
          <el-table-column prop="title" label="案例标题" />
          <el-table-column prop="similarity" label="相似度" width="100">
            <template #default="scope">
              <el-tag type="success">{{ Math.round(scope.row.similarity * 100) }}%</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="solution" label="解决方案" />
        </el-table>
      </div>

      <el-button type="primary" size="large" @click="handleGenerateSolutions" class="next-btn">
        生成改进方案 →
      </el-button>
    </el-card>

    <!-- 步骤4：改进方案 -->
    <el-card v-show="currentStep === 3" class="step-card">
      <template #header><span>步骤4：改进方案</span></template>

      <el-timeline v-if="solutions.length">
        <el-timeline-item
          v-for="(sol, idx) in solutions"
          :key="idx"
          :type="sol.priority === 'P0-紧急' ? 'danger' : sol.priority === 'P1-重要' ? 'warning' : 'primary'"
          :size="sol.priority === 'P0-紧急' ? 'large' : 'normal'"
        >
          <el-card shadow="hover" style="margin-bottom:8px">
            <template #header>
              <div class="solution-header">
                <el-tag :type="sol.priority === 'P0-紧急' ? 'danger' : sol.priority === 'P1-重要' ? 'warning' : 'info'">
                  {{ sol.priority }}
                </el-tag>
                <span style="font-weight:600;margin-left:10px">{{ sol.action }}</span>
              </div>
            </template>
            <el-descriptions :column="2" border>
              <el-descriptions-item label="负责部门">{{ sol.responsible }}</el-descriptions-item>
              <el-descriptions-item label="预估成本">
                <span class="cost">¥{{ Number(sol.estimated_cost).toLocaleString() }}</span>
              </el-descriptions-item>
              <el-descriptions-item label="预期效果" :span="2">{{ sol.expected_effect }}</el-descriptions-item>
              <el-descriptions-item label="实施时间">{{ sol.implementation_time }}</el-descriptions-item>
              <el-descriptions-item label="ROI">{{ sol.roi }}</el-descriptions-item>
            </el-descriptions>
            <div class="solution-actions">
              <el-button type="primary" size="small" @click="createWorkOrder(sol)">创建工单</el-button>
            </div>
          </el-card>
        </el-timeline-item>
      </el-timeline>

      <div class="final-actions">
        <el-button type="success" :icon="Download" @click="exportReport">导出诊断报告</el-button>
        <el-button @click="reset">重新诊断</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElLoading } from 'element-plus'
import { Upload, Loading, Document, Check, UploadFilled, CircleCheck, Clock, Download } from '@element-plus/icons-vue'
import { uploadFile, startDiagnosis as apiStartDiagnosis, generateSolution } from '../api'
import * as echarts from 'echarts'

const router = useRouter()
const currentStep = ref(0)
const uploadedData = ref([])
const totalRecords = ref(0)
const filePath = ref('')
const diagnosisResult = ref(null)
const solutions = ref([])
const diagnosisProgress = ref(0)
const trendChartRef = ref(null)

const analysisParams = reactive({
  equipment: '3号精密磨床',
  days: 7,
  operator: '',
})

const progressSteps = ref([
  { text: '数据清洗完成', done: false, current: false },
  { text: '质量趋势分析完成', done: false, current: false },
  { text: '知识库检索中...', done: false, current: false },
  { text: '人机料法环测6维分析中...', done: false, current: false },
  { text: 'AI大模型推理中...', done: false, current: false },
])

const goBack = () => router.push('/')

const handleFileChange = async (uploadFile) => {
  const file = uploadFile.raw
  try {
    const res = await apiUploadFile(file)
    if (res.data.code === 200) {
      uploadedData.value = res.data.data.records
      totalRecords.value = res.data.data.total_records
      filePath.value = res.data.data.file_path
      ElMessage.success(`文件上传成功！已识别 ${totalRecords.value} 条记录`)
    }
  } catch (e) {
    ElMessage.error('文件上传失败: ' + (e.response?.data?.detail || e.message))
  }
}

async function apiUploadFile(file) {
  const formData = new FormData()
  formData.append('file', file)
  const { default: api } = await import('../api')
  return api.post('/upload/file', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

const startDiagnosis = async () => {
  currentStep.value = 1
  diagnosisProgress.value = 0
  progressSteps.value.forEach(s => { s.done = false; s.current = false })

  const progressInterval = setInterval(() => {
    if (diagnosisProgress.value < 90) {
      diagnosisProgress.value += 10
      const idx = Math.floor(diagnosisProgress.value / 20)
      if (idx > 0) {
        progressSteps.value[idx - 1].done = true
        progressSteps.value[idx - 1].current = false
      }
      if (idx < progressSteps.value.length) {
        progressSteps.value[idx].current = true
      }
    }
  }, 600)

  try {
    const res = await apiStartDiagnosis({
      file_path: filePath.value,
      equipment: analysisParams.equipment,
      days: analysisParams.days,
      operator: analysisParams.operator || null,
    })

    clearInterval(progressInterval)
    diagnosisProgress.value = 100
    progressSteps.value.forEach(s => { s.done = true; s.current = false })

    setTimeout(() => {
      diagnosisResult.value = res.data.data
      currentStep.value = 2
      nextTick(() => drawTrendChart())
    }, 500)
  } catch (e) {
    clearInterval(progressInterval)
    ElMessage.error('诊断失败: ' + (e.response?.data?.detail || e.message))
    currentStep.value = 0
  }
}

const drawTrendChart = () => {
  if (!trendChartRef.value) return
  const chart = echarts.init(trendChartRef.value)
  const trend = diagnosisResult.value?.quality_trend || {}

  chart.setOption({
    title: { text: `${analysisParams.days}天质量合格率趋势`, left: 'center' },
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'category',
      data: trend.dates || ['05-01','05-02','05-03','05-04','05-05','05-06','05-07'],
    },
    yAxis: { type: 'value', min: 85, max: 100, name: '合格率(%)' },
    series: [{
      name: '合格率',
      type: 'line',
      data: trend.rates || [98, 96, 94, 92, 90, 89, 89],
      smooth: true,
      lineStyle: { width: 3 },
      itemStyle: { color: '#409EFF' },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(64,158,255,0.5)' },
          { offset: 1, color: 'rgba(64,158,255,0.1)' },
        ]),
      },
      markLine: {
        data: [{ yAxis: 95, name: '目标线', lineStyle: { color: '#67C23A' } }],
      },
    }],
  })
}

const handleGenerateSolutions = async () => {
  const loading = ElLoading.service({ text: '正在生成改进方案...' })
  try {
    const res = await generateSolution({
      root_causes: diagnosisResult.value.root_causes,
      equipment: analysisParams.equipment,
    })
    solutions.value = res.data.data.solutions
    currentStep.value = 3
  } catch (e) {
    ElMessage.error('方案生成失败')
  } finally {
    loading.close()
  }
}

const exportReport = () => {
  ElMessage.success('诊断报告已导出到下载目录')
}

const createWorkOrder = (solution) => {
  ElMessage.success(`工单已创建：${solution.action}`)
}

const reset = () => {
  currentStep.value = 0
  uploadedData.value = []
  diagnosisResult.value = null
  solutions.value = []
  filePath.value = ''
}
</script>

<style scoped>
.workbench {
  padding: 30px;
  max-width: 1200px;
  margin: 0 auto;
  background: var(--bg-page);
  min-height: 100vh;
}
.steps {
  margin: 40px 0;
}
.step-card {
  margin: 20px 0;
  min-height: 400px;
  border-radius: var(--radius);
}
.params-form {
  margin-top: 24px;
  padding: 16px;
  background: var(--bg-light);
  border-radius: var(--radius);
}
.params-form :deep(.el-form-item__content) {
  width: calc(100% - 100px);
}
.params-form :deep(.el-select) {
  width: 100%;
}
.data-preview {
  margin-top: 24px;
}
.data-preview h4 {
  margin-bottom: 12px;
  color: var(--text-primary);
}
.upload-info {
  margin-top: 16px;
}
.next-btn {
  margin-top: 24px;
  width: 200px;
}
.diagnosis-loading {
  text-align: center;
  padding: 60px 0;
}
.progress-steps {
  margin-top: 40px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-width: 400px;
  margin-left: auto;
  margin-right: auto;
}
.progress-step {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
  color: var(--text-regular);
}
.section-title {
  margin: 20px 0 12px;
  color: var(--text-primary);
}
.trend-section {
  margin: 24px 0;
}
.cause-card {
  margin-bottom: 16px;
}
.cause-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}
.solution-header {
  display: flex;
  align-items: center;
  gap: 12px;
}
.solution-actions {
  margin-top: 16px;
}
.final-actions {
  margin-top: 30px;
  text-align: center;
}
.cost {
  color: var(--warning);
  font-weight: bold;
}
</style>
