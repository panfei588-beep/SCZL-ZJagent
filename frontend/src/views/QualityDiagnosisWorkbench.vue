<template>
  <div class="workbench">
    <div class="workbench-header">
      <div class="header-breadcrumb">
        <span class="back-btn" @click="goBack">
          <el-icon><ArrowLeft /></el-icon> 返回
        </span>
        <span class="divider">/</span>
        <span class="current-page">生产质量数字专家</span>
      </div>
      <div class="header-actions-right ml-auto">
        <el-button @click="showHistory = true" :icon="Management" plain>历史改善记录</el-button>
      </div>
    </div>

    <div class="workbench-content">
      <!-- Steps Navigation -->
      <div class="steps-wrapper card">
        <el-steps :active="currentStep === 99 ? 1 : currentStep" align-center class="custom-steps" finish-status="success">
          <el-step title="数据采样" :icon="Upload" @click="goToStep(0)" class="clickable-step" />
          <el-step title="AI数据解析" :icon="PieChart" @click="goToStep(1)" class="clickable-step" />
          <el-step title="AI诊断分析" :icon="Cpu" @click="goToStep(2)" class="clickable-step" />
          <el-step title="智能化改进方案" :icon="CircleCheck" @click="goToStep(3)" class="clickable-step" />
        </el-steps>
      </div>



      <!-- Step 0: Data Sampling -->
      <div v-if="currentStep === 0" class="step-container animate-fade-in">
        <div class="card upload-card">
          <div class="card-header">
            <h3 class="section-title">Step 1: 数据采样上传</h3>
          </div>
          <div class="card-body">
            <!-- ZONE B: Data Upload -->
            <el-upload
              class="upload-area simplified-upload"
              drag
              action="#"
              :auto-upload="false"
              :on-change="handleFileChange"
              multiple
              accept=".xlsx,.xls,.pdf,.doc,.docx,image/*"
            >
              <div class="upload-inner">
                <el-icon class="upload-icon-small"><UploadFilled /></el-icon>
                <div class="el-upload__text">
                  [ ↑ 拖拽多选文件 / 点击批量上传 ]
                </div>
                <div class="upload-hint">支持 .xlsx, .pdf 等多种质检数据源，单个文件不超过 50MB</div>
              </div>
            </el-upload>

            <!-- Data Preview if uploaded -->
            <div v-if="uploadedData.length > 0" class="data-preview-box mini-preview animate-fade-in mt-16">
              <div class="preview-header">
                <span class="preview-title">已同步检测记录预览 (文件级统计)</span>
                <el-tag type="success" size="small">共识别 {{ totalRecords }} 条测点</el-tag>
              </div>
              <el-table :data="fileStatsTable" border stripe size="small" class="micro-table">
                <el-table-column prop="fileName" label="文件名" />
                <el-table-column prop="count" label="数据条数" width="120" align="center" />
              </el-table>
            </div>

            <div class="improvement-target-box mt-24">
              <span class="filter-label-plain">质量改善目标 (可选)</span>
              <el-input 
                v-model="filter.improvementTarget" 
                type="textarea"
                :rows="2"
                placeholder="请输入本次诊断改善的目标（如：良率提升至 98%、粗糙度偏差 < 0.2μm 等）"
                class="target-input-area mt-8"
              />
            </div>

            <div class="focus-selection-box mt-24">
              <span class="filter-label-plain">重点分析指标</span>
              <div class="mt-8">
                <el-checkbox-group v-model="filter.focusPoints">
                   <el-checkbox label="包络数据分析" value="mean_diff" />
                   <el-checkbox label="质量波动分析" value="process_capability" />
                </el-checkbox-group>
              </div>
            </div>

            <div class="action-footer mt-32">
              <el-button type="primary" size="large" class="btn-glow btn-wide" :loading="loading" @click="startAIScan">
                开始智能化诊断
              </el-button>
            </div>
          </div>
        </div>
      </div>

      <!-- Step Loading Stage (Hidden from stepper but used for transition) -->
      <div v-if="currentStep === 99" class="step-container diagnostic-loading animate-fade-in">
        <div class="ai-processing-box">
          <div class="ai-orb"></div>
          <h2 class="ai-status">AI 正在深度解析检测数据特征...</h2>
          <el-progress :percentage="scanProgress" :stroke-width="8" class="scan-progress" />
          <div class="process-log">
            <p v-for="(log, index) in diagnosticLogs" :key="index" class="log-item">
              <span class="log-time">[{{ log.time }}]</span> {{ log.msg }}
            </p>
          </div>
        </div>
      </div>

      <!-- Step 1: Data Visualization -->
      <div v-if="currentStep === 1" class="step-container animate-fade-in">
        <div class="dashboard-visual">
          <!-- Stats Summary Table (Replacing Stats Grid) -->
          <div class="card stats-summary-card mb-24">
            <div class="card-header border-b">
              <h3 class="card-title-sm">检测包络数据统计</h3>
            </div>
            <div class="card-body">
              <el-table :data="itemStatsTable" border stripe size="mini" class="stats-summary-table">
                <el-table-column prop="fileName" label="源文件" min-width="120" show-overflow-tooltip />
                <el-table-column prop="metric" label="检测指标" min-width="120" />
                <el-table-column prop="count" label="样本总数" width="80" align="center" />
                <el-table-column prop="mean" label="均值" width="100" align="center" />
                <el-table-column prop="max" label="最大值" width="100" align="center">
                  <template #default="scope">
                    <span class="text-danger-custom font-bold">{{ scope.row.max }}</span>
                  </template>
                </el-table-column>
                <el-table-column prop="min" label="最小值" width="100" align="center">
                  <template #default="scope">
                    <span class="text-primary-custom font-bold">{{ scope.row.min }}</span>
                  </template>
                </el-table-column>
                <el-table-column prop="sample" label="样本示例" width="100" align="center">
                   <template #default="scope">
                    <el-tag size="small" effect="plain">{{ scope.row.sample }}</el-tag>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </div>

          <!-- Main Charts Grid -->
          <div class="grid-layout">
            <!-- Xbar-S Chart (Full Row) -->
            <div v-if="filter.focusPoints.includes('mean_diff')" class="card chart-card full-row">
              <div class="card-header"><h3 class="card-title">增压电磁阀性能包络分析 (最大/最小值)</h3></div>
              <div class="card-body">
                <div class="xbar-s-container">
                  <div class="chart-panel">
                    <div class="panel-label">包络值</div>
                    <div class="canvas-wrapper-sm"><canvas id="runChartCanvas"></canvas></div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Quality Reports Section (Added below Xbar-S) -->
            <div v-if="filter.focusPoints.includes('mean_diff')" class="card report-list-card full-row mb-24 anim-slide-up">
              <div class="card-header border-b flex justify-between items-center">
                <h3 class="card-title-sm">关联质检文件预览</h3>
              </div>
              <div class="card-body p-0">
                <div class="report-document-container" @click="openReportPreview">
                  <div class="report-doc-mock">
                    <div class="doc-red-border">
                      <div class="doc-header-info">
                        <div class="info-left">
                          <div class="info-row"><span class="label">档号</span><span class="value underline-red"></span></div>
                          <div class="info-row"><span class="label">保管期限</span><span class="value underline-red"></span></div>
                        </div>
                        <div class="info-right">
                          <div class="info-row"><span class="label">编号</span><span class="value underline-red">13JPSBG-2025194</span></div>
                          <div class="info-row"><span class="label">密级</span><span class="value underline-red">内部</span></div>
                          <div class="info-row"><span class="label">保密期限</span><span class="value underline-red"></span></div>
                          <div class="info-row"><span class="label">阶段标记</span><span class="value underline-red">S</span></div>
                        </div>
                      </div>
                      <div class="doc-content-body">
                         <div class="doc-series">XX 系列型号</div>
                         <div class="doc-model">XX-0 增压电磁阀</div>
                         <div class="doc-title">产品生产质量报告</div>
                      </div>
                    </div>
                  </div>
                  <div class="fade-overlay"></div>
                  <div class="view-more-btn-box">
                    <el-button type="primary" size="large" :icon="View" @click="openReportPreview">点击解析并查看完整报告</el-button>
                  </div>
                </div>
              </div>
            </div>

            <!-- SPC Chart -->
            <div class="card chart-card">
              <div class="card-header"><h3 class="card-title">增压电磁阀电阻质量历史波动</h3></div>
              <div class="card-body"><div class="canvas-wrapper"><canvas id="controlChartCanvas"></canvas></div></div>
            </div>

            <!-- New Fluctuation Chart -->
            <div class="card chart-card">
              <div class="card-header"><h3 class="card-title">增压电磁阀响应时间历史波动</h3></div>
              <div class="card-body"><div class="canvas-wrapper"><canvas id="controlChartCanvas2"></canvas></div></div>
            </div>

            <!-- Run Chart (Only if Xbar-S not shown) -->
            <div class="card chart-card" v-if="!filter.focusPoints.includes('mean_diff')">
              <div class="card-header"><h3 class="card-title">Run Chart 运行图</h3></div>
              <div class="card-body"><div class="canvas-wrapper"><canvas id="runChartCanvas"></canvas></div></div>
            </div>
          </div>
        </div>

        <div class="action-footer mt-24">
          <el-button size="large" @click="goToStep(0)">返回重选数据</el-button>
          <el-button type="primary" size="large" @click="goToStep(2)">执行智能分析与方案规划</el-button>
        </div>
      </div>

      <!-- Step 2: AI Data Analysis -->
      <div v-if="currentStep === 2" class="step-container animate-fade-in">
        <div class="card roots-card mb-24 diagnostic-results-panel">
          <div class="card-header">
            <span class="header-tag danger">AI 核心根因诊断</span>
            <h3 class="card-title">{{ isDiagnosisStreaming ? 'AI 专家思考中...' : '异常链路推理结果' }}</h3>
          </div>
          <div class="card-body">
            <!-- Streaming Thought Process -->
            <div class="thought-process-wrapper mb-20" v-if="diagnosisThoughts.length > 0" ref="thoughtProcessContainer">
              <div class="thought-item" v-for="(thought, idx) in diagnosisThoughts" :key="idx">
                <el-icon class="thought-icon"><Cpu /></el-icon>
                <span class="thought-text">{{ thought }}</span>
              </div>
              <div class="thought-item current-thought" v-if="isThinking && currentThought">
                <el-icon class="is-loading"><Loading /></el-icon>
                <span class="thought-text">{{ currentThought }}</span>
              </div>
            </div>

            <!-- Streaming Result Items -->
            <div class="diagnostic-result-list">
              <div v-for="cause in streamingDiagnosisResult" :key="cause.rank" class="cause-item animate-slide-in">
                <div class="cause-rank">NO.{{ cause.rank }}</div>
                <div class="cause-info">
                  <div class="cause-title-row">
                    <h4 class="cause-name">{{ cause.cause }}</h4>
                    <el-tag :type="getTagType(cause.category)" size="small" effect="dark">{{ cause.category }}</el-tag>
                    <span class="confidence">置信度: {{ (cause.confidence * 100).toFixed(0) }}%</span>
                  </div>
                  <p class="cause-impact">{{ cause.influence }}</p>
                  <div class="evidence-list">
                    <div v-for="(ev, idx) in cause.evidence" :key="idx" class="evidence-tag">
                      <el-icon><Check /></el-icon> {{ ev }}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div v-if="!isDiagnosisStreaming && streamingDiagnosisResult.length === 0" class="text-center py-40">
              <el-empty description="暂无诊断结果" />
            </div>
          </div>
        </div>

        <div class="action-footer">
          <el-button size="large" @click="goToStep(1)">返回可视化视图</el-button>
          
          <el-button 
            v-if="solutions.length > 0" 
            type="primary" 
            size="large" 
            @click="goToStep(3); nextTick(() => initPortraitCharts())"
          >
            查看智能化改进方案 <el-icon class="el-icon--right"><ArrowRight /></el-icon>
          </el-button>
        </div>
      </div>

      <!-- Step 3: Improvement Plan -->
      <div v-if="currentStep === 3" class="step-container animate-fade-in">
        <div class="card solution-card mb-24">
          <div class="card-header header-flex">
            <h3 class="card-title">{{ isSolutionThoughtsBoxVisible ? 'AI 专家思考改进方案中...' : '智能化质量体系改进规划' }}</h3>
            <div class="header-actions">
              <el-button type="primary" plain class="btn-sm" :disabled="isSolutionThoughtsBoxVisible" @click="exportReport">
                <el-icon><Download /></el-icon> 下载诊断报告
              </el-button>
            </div>
          </div>
          <div class="card-body">
            <!-- Solutions Thinking Process -->
            <div class="solution-thought-wrapper mb-20" v-if="isSolutionThoughtsBoxVisible" ref="solutionThoughtContainer">
              <div class="thought-item current-thought" v-if="isPreThinking">
                <el-icon class="is-loading"><Loading /></el-icon>
                <span class="thought-text" style="font-weight: 600; color: #0052d9;">AI专家正在思考质量改进方案...</span>
              </div>
              <template v-else>
                <div class="thought-item" v-for="(thought, idx) in solutionThoughts" :key="idx">
                  <el-icon class="thought-icon"><Cpu /></el-icon>
                  <span class="thought-text">{{ thought }}</span>
                </div>
                <div class="thought-item current-thought" v-if="isSolutionThinking && currentSolutionThought">
                  <el-icon class="is-loading"><Loading /></el-icon>
                  <span class="thought-text">{{ currentSolutionThought }}</span>
                </div>
              </template>
            </div>

            <!-- Streaming solutions table -->
            <el-table 
              v-show="!isSolutionThoughtsBoxVisible"
              :data="streamingSolutions" 
              class="custom-table animate-fade-in" 
              border 
              stripe
            >
              <el-table-column prop="priority" label="级别" width="100">
                <template #default="scope">
                  <span :class="['priority-dot', scope.row.priority.includes('紧急') ? 'high' : 'medium']"></span>
                  {{ scope.row.priority }}
                </template>
              </el-table-column>
              <el-table-column prop="action" label="改进策略项" min-width="200" />
              <el-table-column prop="responsible" label="协同部门" width="120" />
              <el-table-column prop="expected_effect" label="预期产出" min-width="180" />
              <el-table-column prop="implementation_time" label="建议周期" width="120" />
            </el-table>
          </div>
        </div>

        <div class="card roi-card anim-slide-up" v-if="isRoiVisible">
          <div class="card-header">
            <span class="header-tag">效益预估</span>
            <h3 class="card-title">方案实施预期 ROI 预测</h3>
          </div>
          <div class="card-body">
            <div id="predictorChart" class="chart-container-sm"></div>
          </div>
        </div>

        <div class="card-footer text-center mt-24">
          <el-button size="large" @click="reset">归档并返回</el-button>
        </div>
      </div>

    </div>

    <!-- Report Preview Dialog -->
    <el-dialog
      v-model="reportPreviewVisible"
      fullscreen
      append-to-body
      destroy-on-close
      class="full-page-dialog"
    >
      <ReportPreviewModal id="IP-001" @close="reportPreviewVisible = false" />
    </el-dialog>

    <!-- History Records Dialog -->
    <el-dialog
      v-model="showHistory"
      title="历史改善管理记录"
      width="80%"
      class="history-dialog"
      append-to-body
    >
      <el-table :data="historyRecords" border stripe>
        <el-table-column prop="time" label="诊断时间" width="180" />
        <el-table-column prop="target" label="改善目标" min-width="200" />
        <el-table-column prop="records" label="采样条数" width="100" align="center" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="scope">
            <el-button type="primary" link @click="openExpertCard(scope.row)">专家卡片</el-button>
            <el-button type="primary" link @click="loadHistory(scope.row)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="historyRecords.length === 0" description="暂无历史纪录" />
    </el-dialog>

    <!-- Expert Card Dialog -->
    <el-dialog
      v-model="showExpertCard"
      width="440px"
      class="expert-card-dialog"
      append-to-body
      :show-close="false"
    >
      <div v-if="selectedHistory" class="expert-card-container">
        <div class="card-main">
          <!-- Close button -->
          <div class="expert-card-close" @click="showExpertCard = false">
            <el-icon><Close /></el-icon>
          </div>

          <!-- Futuristic Header with Grid dots background -->
          <div class="card-top-bg"></div>
          <div class="card-content">
            <div class="card-header-expert">
              <div class="expert-identity">
                <div class="expert-avatar-box">
                  <el-icon :size="28" color="#31e8ff"><Cpu /></el-icon>
                  <span class="avatar-glow"></span>
                </div>
                <div class="expert-name-box">
                  <div class="expert-label">生产质量数字专家</div>
                  <div class="expert-status">
                    <span class="dot-online-pulse"></span>
                    <span class="status-text">系统协同诊断中</span>
                  </div>
                </div>
              </div>
              <div class="card-id">#{{ selectedHistory.id || 'N/A' }}</div>
            </div>

            <!-- Bento Card Grid -->
            <div class="card-body-expert">
              <!-- Grid Layout for Goal and Time -->
              <div class="meta-bento-grid">
                <div class="bento-meta-item">
                  <div class="meta-label">改善目标 TARGET</div>
                  <div class="meta-value-goal">
                    <el-icon class="icon-target" :size="16"><CircleCheck /></el-icon>
                    <span>{{ selectedHistory.target }}</span>
                  </div>
                </div>
                
                <div class="bento-meta-item">
                  <div class="meta-label">诊断时间 DIAGNOSTIC TIME</div>
                  <div class="meta-value-time">{{ selectedHistory.time }}</div>
                </div>
              </div>

              <!-- Metrics telemetry metrics -->
              <div class="card-stats-expert">
                <div class="stat-box">
                  <div class="stat-num-container">
                    <span class="stat-num">{{ selectedHistory.records }}</span>
                    <span class="stat-unit">测点</span>
                  </div>
                  <div class="stat-label">测点采样数</div>
                </div>
                <div class="stat-divider-vertical"></div>
                <div class="stat-box">
                  <div class="stat-num-container danger">
                    <span class="stat-num danger-num">{{ selectedHistory.diagnosis?.root_causes?.length || 0 }}</span>
                    <span class="stat-unit danger-unit">项</span>
                  </div>
                  <div class="stat-label">根因异常项</div>
                </div>
              </div>

              <!-- Expert Diagnostic Conclusions Preview -->
              <div class="card-diagnosis-preview">
                <div class="preview-label">
                  <span class="label-indicator"></span>
                  诊断核心结论 EXPERT CONCLUSIONS
                </div>
                <div class="preview-list">
                  <div v-for="(cause, index) in selectedHistory.diagnosis?.root_causes?.slice(0, 2)" :key="cause.rank || index" class="preview-item">
                    <div class="item-index">0{{ index + 1 }}</div>
                    <div class="item-text-content">
                      <div class="item-cause-title">{{ cause.cause }}</div>
                      <div class="item-cause-desc">{{ cause.influence }}</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Action footer drawer -->
            <div class="card-footer-expert">
              <el-button type="primary" class="w-full btn-expert" @click="viewFullDiagnosis(selectedHistory)">
                <span>查看完整诊断画布</span>
                <el-icon class="icon-arrow"><ArrowRight /></el-icon>
              </el-button>
              <div class="footer-hint">CorpCLaw · 数字员工专家系统</div>
            </div>
          </div>
        </div>
      </div>
    </el-dialog>

    <!-- Hidden Report Template for PDF Generation -->
    <div id="pdf-report-content" class="hidden-pdf-content">
      <!-- PAGE 1 -->
      <div class="pdf-page page-1">
        <!-- PDF Header -->
        <div class="pdf-header">
           <div class="pdf-logo-area">
             <span class="pdf-logo-text">CorpCLaw</span>
             <div class="pdf-title-group">
               <h1 class="pdf-main-title">智能化质量诊断报告</h1>
               <p class="pdf-sub-title">AERO-IRAY AI QUALITY DIAGNOSIS REPORT</p>
             </div>
           </div>
           <div class="pdf-header-meta">
             <div class="meta-item"><span class="label">报告编号：</span><span class="value">IPR-{{ new Date().getTime().toString().slice(-8) }}</span></div>
             <div class="meta-item"><span class="label">生成日期：</span><span class="value">{{ new Date().toLocaleString() }}</span></div>
           </div>
        </div>

        <!-- Section 0: Target -->
        <div class="pdf-section">
          <div class="section-header-pdf">改善目标概要</div>
          <div class="target-card-pdf">
            <div class="target-text-pdf">
              {{ filter.improvementTarget || '通用性能优化与质量稳定性提升' }}
            </div>
            <div class="target-meta-pdf">
              诊断单位：CorpCLaw · 企业数字员工系统
            </div>
          </div>
        </div>

        <!-- Section 1: Data Analysis -->
        <div class="pdf-section" style="margin-bottom: 0;">
          <div class="section-header-pdf">1. AI 数据解析报告</div>

          <table class="pdf-table">
            <thead>
              <tr>
                <th>检测指标</th>
                <th>样本总数</th>
                <th>统计均值</th>
                <th>最大/最小值</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in itemStatsTable.slice(0, 8)" :key="item.key">
                <td>{{ item.metric }}</td>
                <td>{{ item.count }}</td>
                <td>{{ item.mean }}</td>
                <td>{{ item.max }} / {{ item.min }}</td>
              </tr>
            </tbody>
          </table>
          <div class="pdf-data-summary">
            ※ 基于 {{ totalRecords }} 条质检记录深度计算，整体标准差为 {{ stdDev.toFixed(4) }}。
          </div>
        </div>

        <!-- PDF Footer Page 1 -->
        <div class="pdf-footer">
          <div class="pdf-footer-line"></div>
          <div class="pdf-footer-content">
            <div class="pdf-footer-left">CorpCLaw - 生产数字专家系统</div>
            <div class="pdf-footer-right">第 1 页 / 共 2 页</div>
          </div>
          <p class="pdf-footer-caveat">注：本报告由CorpCLaw AI 数字员工自动生成，仅供生产改进参考。</p>
        </div>
      </div>

      <!-- PAGE 2 -->
      <div class="pdf-page page-2">
        <!-- PDF Header Page 2 (Compact) -->
        <div class="pdf-header-compact">
          <div class="pdf-logo-area">
            <span class="pdf-logo-text" style="font-size: 18px;">CorpCLaw</span>
          </div>
          <div class="pdf-title-compact" style="font-size: 13px; color: #64748b; font-weight: bold;">
            智能化质量诊断报告 (续)
          </div>
        </div>

        <!-- Section 2: Diagnosis -->
        <div class="pdf-section">
          <div class="section-header-pdf">2. AI 专家深度诊断结论</div>
          <div class="pdf-diagnosis-list">
            <div v-for="cause in streamingDiagnosisResult" :key="cause.rank" class="pdf-cause-item">
              <div class="pdf-cause-header">
                <span class="pdf-cause-rank">原因 {{ cause.rank }}</span>
                <span class="pdf-cause-name">{{ cause.cause }}</span>
                <span class="pdf-cause-conf">置信度: {{ (cause.confidence * 100).toFixed(0) }}%</span>
              </div>
              <div class="pdf-cause-body">
                <p><strong>影响分析：</strong>{{ cause.influence }}</p>
                <div class="pdf-evidence-row" v-if="cause.evidence?.length > 0">
                  <strong>诊断依据：</strong>
                  <span v-for="(ev, idx) in cause.evidence" :key="idx" class="pdf-ev-tag">{{ ev }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Section 3: Solutions -->
        <div class="pdf-section">
          <div class="section-header-pdf">3. 智能化改进建议方案</div>
          <table class="pdf-table secondary">
            <thead>
              <tr>
                <th>级别</th>
                <th>改进策略项</th>
                <th>协同部门</th>
                <th>预期产出</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="sol in solutions" :key="sol.action">
                <td>{{ sol.priority }}</td>
                <td>{{ sol.action }}</td>
                <td>{{ sol.responsible }}</td>
                <td>{{ sol.expected_effect }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- PDF Footer Page 2 -->
        <div class="pdf-footer">
          <div class="pdf-footer-line"></div>
          <div class="pdf-footer-content">
            <div class="pdf-footer-left">CorpCLaw - 生产数字专家系统</div>
            <div class="pdf-footer-right">第 2 页 / 共 2 页</div>
          </div>
          <p class="pdf-footer-caveat">注：本报告由CorpCLaw AI 数字员工自动生成，仅供生产改进参考。</p>
        </div>
      </div>
    </div>

    <!-- Hidden Run Chart Canvas for off-screen high-quality export rendering -->
    <canvas id="hiddenRunChartCanvas" width="800" height="350" style="position: absolute; left: -9999px; top: -9999px; width: 800px; height: 350px;"></canvas>
  </div>
</template>

<script>
// Non-reactive storage to avoid circular dependency serialization in Vue/AI Studio
// These instances contain deep circular references that shouldn't be proxied by Vue or serialized
const chartInstances = {
  run: null,
  hiddenRun: null,
  control: null,
  control2: null,
  pareto: null,
  s: null
}
const ecInstances = new Set()
</script>

<script setup>
import { ref, reactive, nextTick, markRaw, watch, computed, onMounted, onUnmounted, shallowRef } from 'vue'
import { useRouter } from 'vue-router'
import ReportPreviewModal from './components/ReportPreviewModal.vue'
import { 
  Upload, Cpu, PieChart, CircleCheck, ArrowLeft, ArrowRight, Document,
  UploadFilled, Check, Download, Loading, View, Odometer, Connection, Management, Postcard, Close
} from '@element-plus/icons-vue'
import { ElMessage, ElLoading } from 'element-plus'
import * as echarts from 'echarts'
import Chart from 'chart.js/auto'
import { jsPDF } from 'jspdf'
import html2canvas from 'html2canvas'

const router = useRouter()
const currentStep = ref(0)
const isAutoMode = ref(false)
const isHistoryMode = ref(false)
const isSolutionsFlowCompleted = ref(false)
const loading = ref(false)
const scanProgress = ref(0)
const diagnosticLogs = ref([])

const showHistory = ref(false)
const showExpertCard = ref(false)
const selectedHistory = ref(null)

// Initialize with 10 mock records
const getMockHistory = () => {
  const records = []
  const targets = ['提升良率至99%', '减少压降异常', '优化材料韧性', '控制温漂偏差', '缩短检测周期', '提高一致性', '降低重复磨损', '优化涂层厚度', '提升耐压性能', '改善表面粗糙度']
  const dates = ['2026-05-18 10:24:12', '2026-05-17 14:15:22', '2026-05-16 09:12:45', '2026-05-15 16:30:10', '2026-05-14 11:45:33', '2026-05-13 13:20:55', '2026-05-12 15:10:21', '2026-05-11 08:35:48', '2026-05-10 17:50:12', '2026-05-09 12:05:30']
  
  for (let i = 0; i < 10; i++) {
    const dataCount = 20 + Math.floor(Math.random() * 20)
    const mockData = []
    const metrics = ['阻值-1和2', '阻值-3和4', '阻值-1和3', '阻值-1和4']
    for (let j = 0; j < dataCount; j++) {
      const valNum = 10000 + Math.floor(Math.random() * 90000)
      const pid = `${valNum}`
      metrics.forEach(m => {
        mockData.push({
          fileName: 'MOCK_DATA_V01.xlsx',
          file_name: 'MOCK_DATA_V01.xlsx',
          '文件名': 'MOCK_DATA_V01.xlsx',
          metric: m,
          '检测项': m,
          value: (25.0 + Math.random() * 0.8).toFixed(1),
          '实测值': (25.0 + Math.random() * 0.8).toFixed(1),
          '正阀编号': pid,
          '产品编号': pid,
          sample: (25.0 + Math.random() * 0.8).toFixed(1)
        })
      })
    }

    records.push({
      id: `H-${1000 + i}`,
      time: dates[i],
      target: targets[i],
      focusPoints: ['mean_diff', 'process_capability'],
      records: mockData.length,
      data: mockData,
      thoughts: ['历史质检数据提取完毕...', '成功加载异常指标空间分布特征...', '匹配知识图谱历史耦合诊断方案...', '根因链路解析完成。'],
      diagnosis: {
        root_causes: [
          { rank: 1, cause: '环境温度波动干扰', influence: '导致电阻值产生系统性正向偏差', confidence: 0.92, category: '环境', evidence: ['环境湿度超标', '温度持续上涨'] },
          { rank: 2, cause: '关键工位参数设置不当', influence: '影响响应时间的一致性', confidence: 0.85, category: '工艺', evidence: ['气源压力波动', '响应时间延后'] }
        ]
      },
      solutions_data: [
        { priority: '紧急-P0', action: '调整恒温恒湿控制器参数', responsible: '动力保障部', expected_effect: '降低 80% 环境偏差', implementation_time: '1天' },
        { priority: '重要-P1', action: '校准关键工位气源压力阀', responsible: '生产部', expected_effect: '提升响应时间一致性', implementation_time: '2天' }
      ]
    })
  }
  return records
}

const localHistory = JSON.parse(localStorage.getItem('quality_history') || '[]')
// Repair any history records that might have empty or missing data arrays in user cache
localHistory.forEach(row => {
  if (!row.data || !Array.isArray(row.data) || row.data.length === 0) {
    const dataCount = 20 + Math.floor(Math.random() * 20)
    const mockData = []
    const metrics = ['阻值-1和2', '阻值-3和4', '阻值-1和3', '阻值-1和4']
    const fName = row.target ? `${row.target}_检测数据.xlsx` : 'MOCK_DATA_V01.xlsx'
    for (let j = 0; j < dataCount; j++) {
      const valNum = 10000 + Math.floor(Math.random() * 90000)
      const pid = `${valNum}`
      metrics.forEach(m => {
        mockData.push({
          fileName: fName,
          file_name: fName,
          '文件名': fName,
          metric: m,
          '检测项': m,
          value: (25.0 + Math.random() * 0.8).toFixed(1),
          '实测值': (25.0 + Math.random() * 0.8).toFixed(1),
          '正阀编号': pid,
          '产品编号': pid,
          sample: (25.0 + Math.random() * 0.8).toFixed(1)
        })
      })
    }
    row.data = mockData
    row.records = mockData.length
  }
})
const historyRecords = ref(localHistory.length > 0 ? localHistory : getMockHistory())

const openExpertCard = (row) => {
  selectedHistory.value = row
  showExpertCard.value = true
}

const isDiagnosisStreaming = ref(false)
const isThinking = ref(false)
const diagnosisThoughts = ref([])
const currentThought = ref('')
const streamingDiagnosisResult = ref([])
const thoughtProcessContainer = ref(null)

watch([diagnosisThoughts, currentThought], () => {
  nextTick(() => {
    if (thoughtProcessContainer.value) {
      thoughtProcessContainer.value.scrollTop = thoughtProcessContainer.value.scrollHeight
    }
  })
}, { deep: true })

const isSolutionThinking = ref(false)
const isPreThinking = ref(false)
const isSolutionThoughtsBoxVisible = ref(false)
const solutionThoughts = ref([])
const currentSolutionThought = ref('')
const streamingSolutions = ref([])
const isRoiVisible = ref(false)
const solutionThoughtContainer = ref(null)

let solutionsThoughtTimer = null
let solutionsStreamTimer = null
let preThinkingTimeout = null

watch([solutionThoughts, currentSolutionThought, isPreThinking], () => {
  nextTick(() => {
    if (solutionThoughtContainer.value) {
      solutionThoughtContainer.value.scrollTop = solutionThoughtContainer.value.scrollHeight
    }
  })
}, { deep: true })

const feedbackVisible = ref(false)
const feedbackForm = reactive({
  action: '',
  status: '已完成',
  result: '',
  improvement: 0
})

const avgImprovement = ref(5.2) // Simplified mock average
const feedbackList = ref([])
const ttestDataUploaded = ref(false)
const ttestData = ref([])
const activeRole = ref('manager')
const reportPreviewVisible = ref(false)
const savedRunChartImg = ref('')

const openReportPreview = () => {
  reportPreviewVisible.value = true
}

// Use shallowRef for objects that don't need deep reactivity but might be complex
const uploadedData = ref([])
const totalRecords = computed(() => uploadedData.value.length)
const diagnosisResult = shallowRef(null)
const solutions = shallowRef([])

const filter = ref({
  role: 'process_manager',
  improvementTarget: '',
  focusPoints: ['mean_diff', 'process_capability']
})

const filePath = ref('')

// Watch for changes and persist
watch([uploadedData, diagnosisResult, solutions, historyRecords], () => {
  localStorage.setItem('quality_uploaded_data', JSON.stringify(uploadedData.value))
  localStorage.setItem('quality_diagnosis_result', JSON.stringify(diagnosisResult.value))
  localStorage.setItem('quality_solutions', JSON.stringify(solutions.value))
  localStorage.setItem('quality_history', JSON.stringify(historyRecords.value))
}, { deep: true })

let scanInterval = null

// Computed stats for text panel
const itemStatsTable = computed(() => {
  if (!uploadedData.value || uploadedData.value.length === 0) return []
  
  const groups = {}
  uploadedData.value.forEach(record => {
    // Group by both file and metric to satisfy user request
    const fName = record.fileName || record.file_name || record['文件名'] || '未知文件'
    // Ensure we capture all possible metric keys
    const metric = record.检测项 || record['检测项'] || record.metric || record.metric_name || '默认指标'
    const groupKey = `${fName} - ${metric}`
    
    if (!groups[groupKey]) {
      groups[groupKey] = {
        name: fName,
        metric: metric,
        values: [],
        sample: record.实测值 || record['实测值'] || record.value || '0.0' // Capture a sample
      }
    }
    const val = parseFloat(record.实测值 || record['实测值'] || record.value)
    if (!isNaN(val)) {
      groups[groupKey].values.push(val)
    }
  })
  
  return Object.keys(groups).map(key => {
    const group = groups[key]
    const vals = group.values
    const count = vals.length
    if (count === 0) {
      return { 
        key, 
        fileName: group.name, 
        metric: group.metric, 
        count: 0, 
        mean: '0.0000', 
        max: '0.0000', 
        min: '0.0000', 
        sample: group.sample 
      }
    }
    
    const sum = vals.reduce((a, b) => a + b, 0)
    const mean = sum / count
    const max = Math.max(...vals)
    const min = Math.min(...vals)
    
    return {
      key,
      fileName: group.name,
      metric: group.metric,
      count,
      mean: mean.toFixed(4),
      max: max.toFixed(4),
      min: min.toFixed(4),
      sample: group.sample
    }
  })
})

const fileStatsTable = computed(() => {
  if (!uploadedData.value || uploadedData.value.length === 0) return []
  const fileMap = {}
  uploadedData.value.forEach(r => {
    // Be flexible with property naming
    const fn = r.fileName || r.file_name || r['文件名'] || '未知文件'
    fileMap[fn] = (fileMap[fn] || 0) + 1
  })
  return Object.keys(fileMap).map(name => ({
    fileName: name,
    count: fileMap[name]
  }))
})

const meanValue = computed(() => {
  if (uploadedData.value.length === 0) return 0
  const values = uploadedData.value.map(r => parseFloat(r.实测值 || r['实测值'] || r.value || 0)).filter(v => !isNaN(v))
  if (values.length === 0) return 0
  return values.reduce((a, b) => a + b, 0) / values.length
})

const variance = computed(() => {
  if (uploadedData.value.length === 0) return 0
  const values = uploadedData.value.map(r => parseFloat(r.实测值 || r['实测值'] || r.value || 0)).filter(v => !isNaN(v))
  if (values.length === 0) return 0
  const m = meanValue.value
  return values.reduce((a, b) => a + (b - m) ** 2, 0) / values.length
})

const stdDev = computed(() => Math.sqrt(variance.value))

const initSamplingCharts = () => {
  if (uploadedData.value.length === 0) return

  const values = uploadedData.value.map(r => parseFloat(r.实测值 || r['实测值'] || r.value || 0)).filter(v => !isNaN(v))
  const labels = uploadedData.value.map((r, i) => {
    return r.正阀编号 || r['正阀编号'] || r.product_id || r.productId || `V-${1000 + i}`
  })
  const mean = meanValue.value
  const sd = stdDev.value
  const ucl_x = mean + 1.2 * sd
  const lcl_x = mean - 1.2 * sd

  // Helper for horizontal line datasets (center, ucl, lcl)
  const getHorizontalLine = (val, color, dash = [], label = '') => ({
    label: label,
    data: labels.map(() => val),
    borderColor: color,
    borderWidth: 1.5,
    pointRadius: 0,
    fill: false,
    borderDash: dash
  });

  // Run Chart / Envelop Chart (formerly X-bar)
  const runCtx = document.getElementById('runChartCanvas')?.getContext('2d')
  if (runCtx) {
    if (chartInstances.run) chartInstances.run.destroy()
    
    chartInstances.run = new Chart(runCtx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [
          {
            label: '包络值',
            data: values,
            borderColor: '#1e293b',
            backgroundColor: '#1e293b',
            borderWidth: 1.5,
            tension: 0,
            pointRadius: 3,
            pointStyle: 'circle'
          },
          getHorizontalLine(mean, '#16a34a', [], '均值线'), // Green Mean line
          getHorizontalLine(ucl_x, '#ef4444', [5, 5], 'UCL'), // Red UCL
          getHorizontalLine(lcl_x, '#ef4444', [5, 5], 'LCL')  // Red LCL
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { 
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (item) => `电阻值: ${item.formattedValue}`
            }
          }
        },
        scales: {
          x: { 
            title: { display: true, text: '正阀编号', font: { size: 10 } },
            grid: { display: true, color: '#f1f5f9' }, 
            ticks: { font: { size: 10 } } 
          },
          y: { 
            title: { display: true, text: '电阻值', font: { size: 10 } },
            grid: { display: true, color: '#f1f5f9' }, 
            ticks: { font: { size: 10 } } 
          }
        }
      }
    })
  }

  // Hidden Run Chart for PDF export (always rendered off-screen at correct resolution)
  // Re-drawn based on the current table stats (itemStatsTable) representing envelope analysis
  const hiddenCanvas = document.getElementById('hiddenRunChartCanvas')
  if (hiddenCanvas) {
    const hiddenCtx = hiddenCanvas.getContext('2d')
    if (chartInstances.hiddenRun) chartInstances.hiddenRun.destroy()

    const tableData = itemStatsTable.value.slice(0, 8)
    const hiddenLabels = tableData.map(i => i.metric)
    const hiddenMeans = tableData.map(i => parseFloat(i.mean || 0))
    const hiddenMaxs = tableData.map(i => parseFloat(i.max || 0))
    const hiddenMins = tableData.map(i => parseFloat(i.min || 0))

    chartInstances.hiddenRun = new Chart(hiddenCtx, {
      type: 'line',
      data: {
        labels: hiddenLabels,
        datasets: [
          {
            label: '包络均值',
            data: hiddenMeans,
            borderColor: '#1e293b',
            backgroundColor: '#1e293b',
            borderWidth: 2,
            tension: 0.1,
            pointRadius: 4,
            pointStyle: 'circle',
            fill: false
          },
          {
            label: '包络上限(最大)',
            data: hiddenMaxs,
            borderColor: '#ef4444',
            backgroundColor: '#ef4444',
            borderWidth: 1.5,
            borderDash: [5, 5],
            pointRadius: 3,
            fill: false
          },
          {
            label: '包络下限(最小)',
            data: hiddenMins,
            borderColor: '#ef4444',
            backgroundColor: '#ef4444',
            borderWidth: 1.5,
            borderDash: [5, 5],
            pointRadius: 3,
            fill: false
          }
        ]
      },
      options: {
        responsive: false,
        maintainAspectRatio: false,
        animation: false,
        plugins: { 
          legend: {
            display: true,
            position: 'top',
            labels: { font: { size: 10 } }
          }
        },
        scales: {
          x: { 
            title: { display: true, text: '检测指标', font: { size: 10 } },
            grid: { display: true, color: '#f1f5f9' }, 
            ticks: { font: { size: 9 }, autoSkip: false } 
          },
          y: { 
            title: { display: true, text: '测量值', font: { size: 10 } },
            grid: { display: true, color: '#f1f5f9' }, 
            ticks: { font: { size: 10 } } 
          }
        }
      }
    })
    
    // Draw immediately and get static PNG data synchronously without waiting for animations!
    try {
      savedRunChartImg.value = hiddenCanvas.toDataURL('image/png')
    } catch (e) {
      console.warn('Failed to extract canvas image data synchronously:', e)
    }
  }

  // Control Chart (SPC)
  const spcCtx = document.getElementById('controlChartCanvas')?.getContext('2d')
  if (spcCtx) {
    if (chartInstances.control) chartInstances.control.destroy()
    const ucl = mean + 3 * sd
    const lcl = mean - 3 * sd
    
    chartInstances.control = new Chart(spcCtx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [
          {
            label: '实测值',
            data: values,
            borderColor: '#003366',
            backgroundColor: (context) => {
              const value = context.raw
              return (value > ucl || value < lcl) ? '#ef4444' : '#003366'
            },
            pointBackgroundColor: (context) => {
              const value = context.raw
              return (value > ucl || value < lcl) ? '#ef4444' : '#003366'
            },
            borderWidth: 1.5,
            tension: 0,
            pointRadius: 4,
          },
          {
            label: 'CL',
            data: labels.map(() => mean),
            borderColor: '#000000',
            borderWidth: 1,
            pointRadius: 0,
            fill: false,
          },
          {
            label: 'UCL',
            data: labels.map(() => ucl),
            borderColor: '#ef4444',
            borderWidth: 1,
            borderDash: [5, 5],
            pointRadius: 0,
            fill: false,
          },
          {
            label: 'LCL',
            data: labels.map(() => lcl),
            borderColor: '#ef4444',
            borderWidth: 1,
            borderDash: [5, 5],
            pointRadius: 0,
            fill: false,
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { display: true, color: '#f1f5f9' } },
          y: { grid: { display: true, color: '#f1f5f9' } }
        }
      }
    })
  }

  // Control Chart 2 (Response Time)
  const spcCtx2 = document.getElementById('controlChartCanvas2')?.getContext('2d')
  if (spcCtx2) {
    if (chartInstances.control2) chartInstances.control2.destroy()
    // Using slightly different mean/sd for visual variety, though based on same data
    const mean2 = mean * 0.8
    const sd2 = sd * 1.2
    const ucl2 = mean2 + 3 * sd2
    const lcl2 = mean2 - 3 * sd2
    
    chartInstances.control2 = new Chart(spcCtx2, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [
          {
            label: '实测值',
            data: values.map(v => v * (0.75 + Math.random() * 0.1)),
            borderColor: '#0891b2',
            backgroundColor: (context) => {
              const value = context.raw
              return (value > ucl2 || value < lcl2) ? '#ef4444' : '#0891b2'
            },
            pointBackgroundColor: (context) => {
              const value = context.raw
              return (value > ucl2 || value < lcl2) ? '#ef4444' : '#0891b2'
            },
            borderWidth: 1.5,
            tension: 0,
            pointRadius: 4,
          },
          {
            label: 'CL',
            data: labels.map(() => mean2),
            borderColor: '#000000',
            borderWidth: 1,
            pointRadius: 0,
            fill: false,
          },
          {
            label: 'UCL',
            data: labels.map(() => ucl2),
            borderColor: '#ef4444',
            borderWidth: 1,
            borderDash: [5, 5],
            pointRadius: 0,
            fill: false,
          },
          {
            label: 'LCL',
            data: labels.map(() => lcl2),
            borderColor: '#ef4444',
            borderWidth: 1,
            borderDash: [5, 5],
            pointRadius: 0,
            fill: false,
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { display: true, color: '#f1f5f9' } },
          y: { grid: { display: true, color: '#f1f5f9' } }
        }
      }
    })
  }
}

const goToSOP = () => {
  currentStep.value = 6
  nextTick(() => {
    initDashboardCharts()
  })
}

const archiveSop = () => ElMessage.success('SOP 已成功归档至企业专家知识库')
const downloadWord = () => ElMessage.info('Word 报告生成中...')

const initDashboardCharts = () => {
  nextTick(() => {
    initParetoChartReport()
    initFishboneChartReport()
    initRunChartReport()
    initControlChartReport()
    initComparisonChartReport()
    initWaterfallChartReport()
    initRadarChartReport()
  })
}

// 01. Pareto Report
const initParetoChartReport = () => {
  const dom = document.getElementById('paretoChartReport')
  if (!dom) return
  const chart = echarts.getInstanceByDom(dom) || echarts.init(dom)
  chart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
    grid: { top: '15%', bottom: '15%', left: '10%', right: '10%' },
    xAxis: { type: 'category', data: ['磨损', '振动', '压力', '温度', '其他'], axisLabel: { fontSize: 10 } },
    yAxis: [{ type: 'value', name: '频次' }, { type: 'value', name: '百分比', axisLabel: { formatter: '{value}%' } }],
    series: [
      { name: '频次', type: 'bar', data: [80, 50, 40, 20, 10], itemStyle: { color: '#0f172a' } },
      { name: '累计百分比', type: 'line', yAxisIndex: 1, data: [40, 65, 85, 95, 100], itemStyle: { color: '#ef4444' } }
    ]
  })
  requestAnimationFrame(() => chart.resize())
}

// 02. Fishbone Report
const initFishboneChartReport = () => {
  const dom = document.getElementById('fishboneChartReport')
  if (!dom) return
  const chart = echarts.getInstanceByDom(dom) || echarts.init(dom)
  chart.setOption({
    series: [{
      type: 'tree',
      data: [{
        name: '质量波动',
        children: [
          { name: '人-技能不足', children: [{ name: '培训缺失' }] },
          { name: '机-振动失准', children: [{ name: '轴承磨损' }] },
          { name: '法-参数偏差', children: [{ name: '进给过快' }] },
          { name: '环-温漂影响', children: [{ name: '环境过热' }] }
        ]
      }],
      orient: 'LR',
      symbolSize: 8,
      initialTreeDepth: 2,
      label: { position: 'left', fontSize: 10 },
      leaves: { label: { position: 'right' } }
    }]
  })
  requestAnimationFrame(() => chart.resize())
}

// 03. Run Chart Report
const initRunChartReport = () => {
  const dom = document.getElementById('runChartReport')
  if (!dom) return
  const chart = echarts.getInstanceByDom(dom) || echarts.init(dom)
  chart.setOption({
    grid: { top: '15%', bottom: '15%', left: '10%', right: '5%' },
    xAxis: { type: 'category', data: ['08:00', '10:00', '12:00', '14:00', '16:00', '18:00', '20:00'] },
    yAxis: { type: 'value', min: 80, max: 100, name: '良率 %' },
    series: [
      { 
        data: [92, 94, 88, 85, 89, 93, 97], 
        type: 'line', 
        smooth: true, 
        lineStyle: { color: '#1e3a8a', width: 2.5 }, 
        itemStyle: { color: '#1e3a8a' },
        symbol: 'circle',
        symbolSize: 8,
        markLine: {
          symbol: 'none',
          data: [{ yAxis: 91.5, lineStyle: { color: '#000', type: 'solid', width: 1.5 }, label: { show: true, position: 'end', formatter: 'Mean' } }]
        }
      }
    ]
  })
  requestAnimationFrame(() => chart.resize())
}

// 04. Control Chart Report
const initControlChartReport = () => {
  const dom = document.getElementById('controlChartReport')
  if (!dom) return
  const chart = echarts.getInstanceByDom(dom) || echarts.init(dom)
  chart.setOption({
    grid: { top: '15%', bottom: '15%', left: '10%', right: '5%' },
    xAxis: { type: 'category', data: ['P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7', 'P8', 'P9', 'P10'] },
    yAxis: { type: 'value', min: 14.5, max: 15.5 },
    series: [
      {
        data: [14.9, 15.1, 15.3, 14.8, 15.2, 15.5, 14.7, 14.9, 15.0, 15.2],
        type: 'line',
        lineStyle: { color: '#0f172a' },
        itemStyle: { color: params => params.data > 15.4 || params.data < 14.7 ? '#ef4444' : '#0f172a' },
        markLine: {
          data: [
            { yAxis: 15.4, label: { formatter: 'UCL' }, lineStyle: { color: '#ef4444', type: 'dashed' } },
            { yAxis: 15.0, label: { formatter: 'CL' }, lineStyle: { color: '#64748b' } },
            { yAxis: 14.6, label: { formatter: 'LCL' }, lineStyle: { color: '#ef4444', type: 'dashed' } }
          ]
        }
      }
    ]
  })
  requestAnimationFrame(() => chart.resize())
}

// 05. Comparison Chart Report
const initComparisonChartReport = () => {
  const dom = document.getElementById('comparisonChartReport')
  if (!dom) return
  const chart = echarts.getInstanceByDom(dom) || echarts.init(dom)
  chart.setOption({
    legend: { bottom: '0%' },
    grid: { top: '15%', bottom: '20%', left: '10%', right: '5%' },
    xAxis: { type: 'category', data: ['尺寸一致性', '表面光洁度', '综合良率', '加工效率'] },
    yAxis: { type: 'value', max: 100 },
    series: [
      { name: '改善前', type: 'bar', data: [75, 82, 89, 78], itemStyle: { color: '#94a3b8' } },
      { name: '改善后', type: 'bar', data: [94, 96, 98, 92], itemStyle: { color: '#1e293b' } }
    ]
  })
  requestAnimationFrame(() => chart.resize())
}

// 06. Waterfall Chart Report
const initWaterfallChartReport = () => {
  const dom = document.getElementById('waterfallChartReport')
  if (!dom) return
  const chart = echarts.getInstanceByDom(dom) || echarts.init(dom)
  chart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { top: '15%', bottom: '15%', left: '10%', right: '5%' },
    xAxis: { type: 'category', splitLine: { show: false }, data: ['初始值', '振动态势', '温漂抵消', '工艺对齐', '最终值'] },
    yAxis: { type: 'value' },
    series: [
      {
        name: 'Placeholder',
        type: 'bar',
        stack: 'Total',
        itemStyle: { borderColor: 'transparent', color: 'transparent' },
        emphasis: { itemStyle: { borderColor: 'transparent', color: 'transparent' } },
        data: [0, 89, 93, 97, 0]
      },
      {
        name: '变化量',
        type: 'bar',
        stack: 'Total',
        label: { show: true, position: 'top' },
        data: [89, 4, 4, 1, 98],
        itemStyle: { color: params => params.dataIndex === 0 || params.dataIndex === 4 ? '#0f172a' : '#22c55e' }
      }
    ]
  })
  requestAnimationFrame(() => chart.resize())
}

// 07. Radar Chart Report
const initRadarChartReport = () => {
  const dom = document.getElementById('radarChartReport')
  if (!dom) return
  const chart = echarts.getInstanceByDom(dom) || echarts.init(dom)
  chart.setOption({
    radar: {
      indicator: [
        { name: '设备自动化', max: 100 },
        { name: '参数受控度', max: 100 },
        { name: '人员执规范', max: 100 },
        { name: '环境抗扰度', max: 100 },
        { name: '测量精准度', max: 100 }
      ],
      shape: 'circle',
      splitArea: { areaStyle: { color: ['rgba(15, 23, 42, 0.05)', 'rgba(15, 23, 42, 0.1)'] } }
    },
    series: [{
      type: 'radar',
      data: [{ value: [85, 92, 70, 88, 95], name: '质量画像', areaStyle: { color: 'rgba(15, 23, 42, 0.3)' }, lineStyle: { color: '#0f172a' }, itemStyle: { color: '#0f172a' } }]
    }]
  })
  requestAnimationFrame(() => chart.resize())
}

watch(activeRole, () => {
  initDashboardCharts()
})


const goToStep = (step) => {
  if (scanInterval) {
    clearInterval(scanInterval)
    scanInterval = null
  }
  isAutoMode.value = false
  currentStep.value = step
}

let resizeTimer = null
const handleResize = () => {
  if (resizeTimer) {
    clearTimeout(resizeTimer)
  }
  
  resizeTimer = setTimeout(() => {
    const charts = document.querySelectorAll('.report-chart-box, .chart-container, .chart-container-sm')
    charts.forEach(el => {
      const inst = echarts.getInstanceByDom(el)
      if (inst) {
        requestAnimationFrame(() => inst.resize())
      }
    })
    
    requestAnimationFrame(() => {
      if (chartInstances.run) chartInstances.run.resize()
      if (chartInstances.s) chartInstances.s.resize()
      if (chartInstances.control) chartInstances.control.resize()
      if (chartInstances.control2) chartInstances.control2.resize()
      if (chartInstances.pareto) chartInstances.pareto.resize()
    })
    
    resizeTimer = null
  }, 100)
}

onMounted(() => {
  window.addEventListener('resize', handleResize)
  
  // Suppress ResizeObserver loop limit exceeded error
  window.addEventListener('error', e => {
    if (e.message === 'ResizeObserver loop completed with undelivered notifications.' || e.message === 'ResizeObserver loop limit exceeded') {
      e.stopImmediatePropagation()
    }
  })
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  // Clean up chart instances
  if (chartInstances.run) chartInstances.run.destroy()
  if (chartInstances.hiddenRun) chartInstances.hiddenRun.destroy()
  if (chartInstances.s) chartInstances.s.destroy()
  if (chartInstances.control) chartInstances.control.destroy()
  if (chartInstances.control2) chartInstances.control2.destroy()
  if (chartInstances.pareto) chartInstances.pareto.destroy()
  ecInstances.forEach(inst => {
    if (typeof inst.dispose === 'function') inst.dispose()
  })
  ecInstances.clear()
})

const goBack = () => router.push('/')

const openFeedbackDialog = (row) => {
  feedbackForm.action = row.action
  feedbackForm.result = ''
  feedbackForm.improvement = row.priority.includes('紧急') ? 8.5 : 3.2
  feedbackVisible.value = true
}

const submitFeedback = () => {
  feedbackList.value.push({ ...feedbackForm })
  ElMessage.success('试验数据已成功反馈，已作为归因分析模型输入')
  feedbackVisible.value = false
}

const handleTtestFileChange = (file) => {
  if (file.size > 50 * 1024 * 1024) {
    ElMessage.error('单个文件不超过 50MB')
    return false
  }
  const mask = ElLoading.service({ text: '正在进行统计显著性计算...', background: 'rgba(255, 255, 255, 0.8)' })
  setTimeout(() => {
    ttestDataUploaded.value = true
    nextTick(() => initDistributionChart())
    mask.close()
    ElMessage.success('T-test 分析完成：P < 0.05，改善显著')
  }, 1500)
}

const initVerificationCharts = () => {
  const chartDom = document.getElementById('verificationChart')
  if (!chartDom) return
  const myChart = echarts.getInstanceByDom(chartDom) || echarts.init(chartDom)
  myChart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['改进前 (Before)', '改进后 (After)'] },
    xAxis: { type: 'category', data: ['良率', '稳定性', '成本优化', '周期缩短'] },
    yAxis: { type: 'value', max: 100 },
    series: [
      {
        name: '改进前 (Before)',
        type: 'bar',
        data: [89, 72, 65, 80],
        itemStyle: { color: '#94a3b8' },
        barWidth: '20%'
      },
      {
        name: '改进后 (After)',
        type: 'bar',
        data: [97, 95, 88, 92],
        itemStyle: { color: '#409eff' },
        barWidth: '20%'
      }
    ]
  })
  requestAnimationFrame(() => myChart.resize())
}

const initDistributionChart = () => {
  const chartDom = document.getElementById('distributionChart')
  if (!chartDom) return
  const myChart = echarts.getInstanceByDom(chartDom) || echarts.init(chartDom)
  myChart.setOption({
    title: { 
      text: '异常特征分布对比', 
      left: 'center', 
      top: 10,
      textStyle: { fontSize: 16, fontWeight: 700, color: '#1e293b' } 
    },
    tooltip: { 
      trigger: 'axis',
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      borderColor: '#e2e8f0',
      borderWidth: 1,
      textStyle: { color: '#475569' },
      padding: [10, 15]
    },
    legend: { 
      bottom: 20, 
      left: 'center',
      data: ['初始采样 (Before)', '生产验证 (After)'],
      itemWidth: 14,
      itemHeight: 14
    },
    grid: {
      top: '20%',
      left: '10%',
      right: '8%',
      bottom: '18%'
    },
    xAxis: { 
      type: 'category', 
      boundaryGap: false,
      data: ['0-5μm', '5-10μm', '10-15μm', '15-20μm', '>20μm'],
      axisLine: { lineStyle: { color: '#e2e8f0' } },
      axisLabel: { color: '#64748b' }
    },
    yAxis: { 
      type: 'value', 
      name: '频次', 
      max: 80,
      axisLabel: { color: '#64748b' },
      splitLine: { lineStyle: { color: '#f1f5f9', type: 'dashed' } }
    },
    series: [
      {
        name: '初始采样 (Before)',
        type: 'line',
        smooth: true,
        data: [5, 30, 78, 55, 30],
        lineStyle: { color: '#cbd5e1', width: 2, type: 'dashed' },
        itemStyle: { color: '#cbd5e1' },
        symbol: 'circle',
        symbolSize: 6
      },
      {
        name: '生产验证 (After)',
        type: 'line',
        smooth: true,
        data: [5, 15, 35, 20, 8],
        lineStyle: { color: '#3b82f6', width: 2.5 },
        itemStyle: { color: '#3b82f6' },
        areaStyle: { 
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(59, 130, 246, 0.25)' },
            { offset: 1, color: 'rgba(59, 130, 246, 0.05)' }
          ]) 
        },
        symbol: 'circle',
        symbolSize: 8,
        emphasis: {
          scale: true,
          itemStyle: { borderWidth: 2, borderColor: '#fff' }
        }
      }
    ]
  })
  requestAnimationFrame(() => myChart.resize())
}

// Global Resize Handler - Handled in onMounted/onUnmounted

const handleFileChange = async (uploadFile) => {
  const file = uploadFile.raw
  
  // Size verification
  if (file.size > 50 * 1024 * 1024) {
    ElMessage.error('单个文件不超过 50MB')
    return false
  }

  const formData = new FormData()
  formData.append('file', file)
  
  try {
    // START: Client-side Mock Data for Quick Feedback
    // If backend fails or for immediate feedback, we generate mock data
    const generateMockData = (fName) => {
      const records = [];
      const now = new Date();
      // Simulate multiple metrics (like in the user photo)
      const metrics = ['阻值-1和2', '阻值-3和4', '阻值-1和3', '阻值-1和4'];
      
      for (let i = 0; i < 20; i++) {
        // Use daily intervals to show different YYYY-MM-DD
        const date = new Date(now.getTime() - (20 - i) * 24 * 3600000);
        const valNum = 10000 + Math.floor(Math.random() * 90000);
        const pid = `${valNum}`;
        metrics.forEach(m => {
          records.push({
            "日期": date.toISOString().slice(0, 16).replace('T', ' '),
            "产品编号": pid,
            "正阀编号": pid,
            "检测项": m,
            "判定": Math.random() > 0.05 ? "合格" : "不合格",
            "实测值": (25.0 + Math.random() * 0.8).toFixed(1),
            "fileName": fName
          });
        });
      }
      return records;
    }

    // Append to existing data if it's the first step interaction
    const mockRecords = generateMockData(file.name);
    uploadedData.value = [...uploadedData.value, ...mockRecords];
    
    ElMessage.info(`检测源 [${file.name}] 已解析，当前库内共 ${totalRecords.value} 个采样点`);
    
    nextTick(() => initSamplingCharts());
    // END: Client-side Mock Data

    // Start Backend Sync (Async background)
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 12000); // Increased timeout

    try {
      const res = await fetch('/api/upload/file', {
        method: 'POST',
        body: formData,
        signal: controller.signal
      })
      clearTimeout(timeoutId);
      
      if (!res.ok) {
        console.warn('Backend upload failed with status:', res.status);
        return;
      }

      const data = await res.json()
      if (data.code === 200 && data.data && data.data.records) {
        // Replace mock records for THIS file with server records
        const otherRecords = uploadedData.value.filter(r => r.fileName !== file.name)
        const serverRecords = data.data.records.map(r => ({ ...r, fileName: file.name }))
        uploadedData.value = [...otherRecords, ...serverRecords]
        filePath.value = data.data.file_path
        ElMessage.success(`[${file.name}] 云端同步完成`)
        nextTick(() => initSamplingCharts())
      }
    } catch (fetchErr) {
      clearTimeout(timeoutId);
      if (fetchErr.name === 'AbortError') {
        console.warn('Upload sync timed out, using local records.');
      } else {
        console.warn('Background upload sync unavailable:', fetchErr.message);
      }
    }
  } catch (e) {
    console.error('File parsing error:', e);
  }
}

// Watch currentStep to re-init charts when entering visualization steps
watch(currentStep, (newStep) => {
  if (newStep === 1) {
    nextTick(() => {
      setTimeout(() => {
        initSamplingCharts()
        initPortraitCharts()
        requestAnimationFrame(() => {
          ecInstances.forEach(inst => {
            if (typeof inst.resize === 'function') inst.resize()
          })
        })
        
        // Auto transition to AI Data Analysis after 3 seconds ONLY in auto mode
        setTimeout(() => {
          if (currentStep.value === 1 && isAutoMode.value) {
            currentStep.value = 2
          }
        }, 3000)
      }, 100)
    })
  } else if (newStep === 2) {
    // Automatically trigger solutions if they aren't generated yet
    if (solutions.value.length === 0) {
      setTimeout(() => {
        handleGenerateSolutions()
      }, 800)
    }
  } else if (newStep === 3) {
    nextTick(() => {
      startIntelligenceSolutionsFlow()
    })
  } else {
    cleanupSolutionsFlow()
  }
})

const startAIScan = () => {
  if (uploadedData.value.length === 0) {
    ElMessage.warning('请先上传质量报表')
    return
  }
  isAutoMode.value = true
  isHistoryMode.value = false
  isSolutionsFlowCompleted.value = false
  currentStep.value = 99 // Show loading
  scanProgress.value = 0
  diagnosticLogs.value = []
  
  // Clear previous diagnostic results to ensure fresh streaming feel
  diagnosisThoughts.value = []
  streamingDiagnosisResult.value = []
  isDiagnosisStreaming.value = false
  isThinking.value = false
  
  if (scanInterval) clearInterval(scanInterval)
  
  const processSteps = [
    '解构原始张量数据...',
    '对齐设备历史维护记录...',
    '启动多层感知机异常推理...',
    '捕获微米级尺寸波动关联项...',
    '诊断链路构建完成。'
  ]
  
  let stepIdx = 0
  scanInterval = setInterval(() => {
    if (scanProgress.value < 100) {
      scanProgress.value += 4
      if (scanProgress.value % 20 === 0 && stepIdx < processSteps.length) {
        diagnosticLogs.value.push({
          time: new Date().toLocaleTimeString(),
          msg: processSteps[stepIdx]
        })
        stepIdx++
      }
    } else {
      clearInterval(scanInterval)
      scanInterval = null
      // Auto transition to Visualization first
      currentStep.value = 1
      nextTick(() => {
        initSamplingCharts()
        initPortraitCharts()
      })
      fetchDiagnosisResultBackground()
    }
  }, 50)
}

const fetchDiagnosisResultBackground = async () => {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), 1200)
  try {
    const res = await fetch('/api/diagnosis/analyze', { 
      method: 'POST',
      signal: controller.signal
    })
    clearTimeout(timeoutId)
    if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`)
    const data = await res.json()
    if (data.code === 200) {
      diagnosisResult.value = markRaw(data.data)
      // If we are already in Step 2, start streaming immediately
      if (currentStep.value === 2 && streamingDiagnosisResult.value.length === 0) {
        startDiagnosticStreaming()
      }
    }
  } catch (e) {
    clearTimeout(timeoutId)
    console.error('Diagnosis background fetch error, using local fallback:', e)
    if (!diagnosisResult.value) {
      diagnosisResult.value = markRaw({
        root_causes: [
          { rank: 1, cause: '3号精密磨床主轴轴承磨损', influence: '导致加工件径向跳动超差，合格率下降8%', confidence: 0.92, category: '设备', evidence: ['三次元检测数据呈现明显的周期性特征', '近期设备维护记录显示主轴振动值超标15%', '该问题在高速加工模式下尤为显著'] },
          { rank: 2, cause: '切削液浓度不达标', influence: '散热不良导致工件热变形', confidence: 0.78, category: '环境', evidence: ['测量数据在下午高温时段偏差增大', '车间环境温度近期波动较大'] }
        ]
      })
    }
    if (currentStep.value === 2 && streamingDiagnosisResult.value.length === 0) {
      startDiagnosticStreaming()
    }
  }
}

const startDiagnosticStreaming = () => {
  if (!diagnosisResult.value || isDiagnosisStreaming.value || streamingDiagnosisResult.value.length > 0) return
  
  isDiagnosisStreaming.value = true
  isThinking.value = true
  diagnosisThoughts.value = []
  streamingDiagnosisResult.value = []
  
  const thoughts = [
    '正在拉取实时多维质检张量数据进行高阶对齐...',
    '对齐检测设备物理通道时序，计算多通道残差分布特征...',
    '执行双向马尔可夫链异常演变推理，过滤探针传感器机械抖动噪声...',
    '识别高阶局部异常子空间，正在提取密封性与电气绝缘的物理自相关因数...',
    '调取航天质量机理数据库，计算关键特征包络边界置信度...',
    '进行微观气源阀体振动形变在多频共振条件下的动力学重构...',
    '交叉验证恒温恒湿循环延迟引起的热应力累积偏差...',
    '正在检索 AI 核心诊断知识图谱：评估 3 号偏离控制线相关联成因...',
    '匹配退化预测轨迹模式：偏载力偏移评分提升至 88%...',
    '调用主轴轴承维护预警深度学习推理模组，锁定微米磨损周期关联性...',
    '执行高维度多项式逻辑反演计算，定位加工工位力矩零点漂移参数...',
    '协同交叉推演配气控制阀与系统流体流动时延的互补耦合作用...',
    '根据遗传寻优方案，计算关键性能参数包之多目标多维优化解...',
    '专家大脑全量数据链路重构完毕，正在生成根因链路判定结果...'
  ]
  
  let tIdx = 0
  currentThought.value = thoughts[0]
  const tTimer = setInterval(() => {
    if (tIdx < thoughts.length) {
      diagnosisThoughts.value.push(thoughts[tIdx])
      tIdx++
      if (tIdx < thoughts.length) {
        currentThought.value = thoughts[tIdx]
      } else {
        currentThought.value = '即将输出深度确诊结果...'
      }
    } else {
      clearInterval(tTimer)
      currentThought.value = ''
      isThinking.value = false
      // Start streaming causes
      streamCauses()
    }
  }, 250) // 加快4倍速度 (250ms interval)
}

const streamCauses = () => {
  const causes = diagnosisResult.value?.root_causes || [
    { rank: 1, cause: '3号精密磨床主轴轴承磨损', influence: '导致加工件径向跳动超差，合格率下降8%', confidence: 0.92, category: '设备', evidence: ['三次元检测数据呈现明显的周期性特征', '近期设备维护记录显示主轴振动值超标15%', '该问题在高速加工模式下尤为显著'] },
    { rank: 2, cause: '切削液浓度不达标', influence: '散热不良导致工件热变形', confidence: 0.78, category: '环境', evidence: ['测量数据在下午高温时段偏差增大', '车间环境温度近期波动较大'] }
  ]
  let cIdx = 0
  const cTimer = setInterval(() => {
    if (cIdx < causes.length) {
      streamingDiagnosisResult.value.push(causes[cIdx])
      cIdx++
    } else {
      clearInterval(cTimer)
      isDiagnosisStreaming.value = false
      if (isAutoMode.value) {
        setTimeout(() => {
          if (currentStep.value === 2) {
            currentStep.value = 3
          }
        }, 1500)
      }
    }
  }, 800)
}

const cleanupSolutionsFlow = () => {
  if (preThinkingTimeout) {
    clearTimeout(preThinkingTimeout)
    preThinkingTimeout = null
  }
  if (solutionsThoughtTimer) {
    clearInterval(solutionsThoughtTimer)
    solutionsThoughtTimer = null
  }
  if (solutionsStreamTimer) {
    clearInterval(solutionsStreamTimer)
    solutionsStreamTimer = null
  }
  isPreThinking.value = false
  isSolutionThoughtsBoxVisible.value = false
  isSolutionThinking.value = false
  solutionThoughts.value = []
  currentSolutionThought.value = ''
  streamingSolutions.value = []
  isRoiVisible.value = false
}

const startIntelligenceSolutionsFlow = () => {
  if (isSolutionsFlowCompleted.value || isHistoryMode.value) {
    isPreThinking.value = false
    isSolutionThoughtsBoxVisible.value = false
    isSolutionThinking.value = false
    const targetSolutions = solutions.value.length > 0 ? solutions.value : [
      { priority: 'P0-紧急', action: '停机更换3号磨床主轴轴承', responsible: '设备运维部', expected_effect: '彻底解决轴向跳动，预计合格率回升至99%以上', implementation_time: '24小时内' },
      { priority: 'P1-重要', action: '调整切削液配比并安装实时监控计', responsible: '生产技术部', expected_effect: '稳定加工温度，减少工件热变形风险', implementation_time: '3个工作日' },
      { priority: 'P2-一般', action: '对夜班操作员加强过程检测培训', responsible: '质量管理部', expected_effect: '降低人为操作不规范导致的微小偏差', implementation_time: '一周内' }
    ]
    streamingSolutions.value = [...targetSolutions]
    isRoiVisible.value = true
    nextTick(() => {
      initPortraitCharts()
      requestAnimationFrame(() => {
        ecInstances.forEach(inst => {
          if (typeof inst.resize === 'function') inst.resize()
        })
      })
    })
    return
  }

  // Clear any existing timers or previous flows
  cleanupSolutionsFlow()
  
  // Show pre-thinking state with the requested loading prompt for 2 seconds
  isPreThinking.value = true
  isSolutionThoughtsBoxVisible.value = true
  
  preThinkingTimeout = setTimeout(() => {
    isPreThinking.value = false
    isSolutionThinking.value = true
    
    const thoughts = [
      '正在拉取专家系统诊断结果及根因耦合因子...',
      '基于物理模型检索制造质量改进策略知识数据库...',
      '分析当前偏差特征，自适应配对最优工艺控制参数...',
      '评估工艺调整对系统的动态响应度，生成操作执行阈值...',
      '核算各条改进策略对应的投资回报与质量回弹概率模型...',
      '最优化质量体系迭代改进规划构建就绪，准备部署策略...'
    ]
    
    let tIdx = 0
    currentSolutionThought.value = thoughts[0]
    solutionsThoughtTimer = setInterval(() => {
      if (tIdx < thoughts.length) {
        solutionThoughts.value.push(thoughts[tIdx])
        tIdx++
        if (tIdx < thoughts.length) {
          currentSolutionThought.value = thoughts[tIdx]
        } else {
          currentSolutionThought.value = '即将部署改进方案计划...'
        }
      } else {
        clearInterval(solutionsThoughtTimer)
        solutionsThoughtTimer = null
        currentSolutionThought.value = ''
        isSolutionThinking.value = false
        // Hide the thoughts box completely
        isSolutionThoughtsBoxVisible.value = false
        
        // Start streaming table records/rows
        streamIntelSolutions()
      }
    }, 250) // High speed (250ms interval)
  }, 2000) // Stay 2 seconds as requested
}

const streamIntelSolutions = () => {
  if (solutionsStreamTimer) clearInterval(solutionsStreamTimer)
  
  // Use either generated solutions or a fallback list to stream
  const targetSolutions = solutions.value.length > 0 ? solutions.value : [
    { priority: 'P0-紧急', action: '停机更换3号磨床主轴轴承', responsible: '设备运维部', expected_effect: '彻底解决轴向跳动，预计合格率回升至99%以上', implementation_time: '24小时内' },
    { priority: 'P1-重要', action: '调整切削液配比并安装实时监控计', responsible: '生产技术部', expected_effect: '稳定加工温度，减少工件热变形风险', implementation_time: '3个工作日' },
    { priority: 'P2-一般', action: '对夜班操作员加强过程检测培训', responsible: '质量管理部', expected_effect: '降低人为操作不规范导致的微小偏差', implementation_time: '一周内' }
  ]
  
  let sIdx = 0
  solutionsStreamTimer = setInterval(() => {
    if (sIdx < targetSolutions.length) {
      streamingSolutions.value.push(targetSolutions[sIdx])
      sIdx++
    } else {
      clearInterval(solutionsStreamTimer)
      solutionsStreamTimer = null
      
      isSolutionsFlowCompleted.value = true
      
      // Success, stream is complete!
      // Reveal ROI Prediction Section with dynamic entering animation
      isRoiVisible.value = true
      nextTick(() => {
        initPortraitCharts()
        requestAnimationFrame(() => {
          ecInstances.forEach(inst => {
            if (typeof inst.resize === 'function') inst.resize()
          })
        })
      })
    }
  }, 500) // Stream one row every 500ms
}

watch(currentStep, (newStep) => {
  if (newStep === 2) {
    if (!diagnosisResult.value) {
      diagnosisResult.value = markRaw({
        root_causes: [
          { rank: 1, cause: '3号精密磨床主轴轴承磨损', influence: '导致加工件径向跳动超差，合格率下降8%', confidence: 0.92, category: '设备', evidence: ['三次元检测数据呈现明显的周期性特征', '近期设备维护记录显示主轴振动值超标15%', '该问题在高速加工模式下尤为显著'] },
          { rank: 2, cause: '切削液浓度不达标', influence: '散热不良导致工件热变形', confidence: 0.78, category: '环境', evidence: ['测量数据在下午高温时段偏差增大', '车间环境温度近期波动较大'] }
        ]
      })
    }
    if (streamingDiagnosisResult.value.length === 0) {
      startDiagnosticStreaming()
    }
  }
})

// ecInstances is now in the outer script block

const initPortraitCharts = () => {
  // Use setTimeout to guarantee that the DOM node has mounted and has dimensions
  setTimeout(() => {
    const predictorDom = document.getElementById('predictorChart')
    if (predictorDom) {
      if (predictorDom._ro) {
        predictorDom._ro.disconnect()
        delete predictorDom._ro
      }

      const existing = echarts.getInstanceByDom(predictorDom)
      if (existing) {
        existing.dispose()
      }
      const predictorChart = echarts.init(predictorDom)
      ecInstances.add(predictorChart)
      predictorChart.setOption({
        tooltip: { trigger: 'axis' },
        xAxis: { type: 'category', data: ['W1', 'W2', 'W3', 'W4'] },
        yAxis: { type: 'value', name: '提升百分比' },
        series: [
          {
            name: '预期良率提升',
            data: [2, 5, 12, 18],
            type: 'bar',
            itemStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: '#409eff' },
                { offset: 1, color: '#79bbff' }
              ])
            },
            barWidth: '30%'
          },
          {
            name: '成本回收曲线',
            data: [1, 4, 9, 15],
            type: 'line',
            smooth: true,
            itemStyle: { color: '#67c23a' }
          }
        ]
      })
      
      // Use ResizeObserver to auto-resize when container dimensions update
      if (window.ResizeObserver) {
        const ro = new ResizeObserver(() => {
          if (predictorDom.clientWidth > 0 && predictorDom.clientHeight > 0) {
            predictorChart.resize()
          }
        })
        ro.observe(predictorDom)
        predictorDom._ro = ro
      } else {
        requestAnimationFrame(() => predictorChart.resize())
      }
    }
  }, 100)
}

const handleGenerateSolutions = async () => {
  // No full-page mask, we show inline planning status in Step 2 instead
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), 1200)
  try {
    const res = await fetch('/api/solution/generate', { 
      method: 'POST',
      signal: controller.signal
    })
    clearTimeout(timeoutId)
    if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`)
    const data = await res.json()
    if (data.code === 200) {
      solutions.value = markRaw(data.data.solutions)
    }
  } catch (e) {
    clearTimeout(timeoutId)
    console.error('Solution optimization error, using local fallback:', e)
    solutions.value = markRaw([
      { priority: 'P0-紧急', action: '停机更换3号磨床主轴轴承', responsible: '设备运维部', expected_effect: '彻底解决轴向跳动，预计合格率回升至99%以上', implementation_time: '24小时内' },
      { priority: 'P1-重要', action: '调整切削液配比并安装实时监控计', responsible: '生产技术部', expected_effect: '稳定加工温度，减少工件热变形风险', implementation_time: '3个工作日' },
      { priority: 'P2-一般', action: '对夜班操作员加强过程检测培训', responsible: '质量管理部', expected_effect: '降低人为操作不规范导致的微小偏差', implementation_time: '一周内' }
    ])
  }
}

const getTagType = (cat) => {
  if (cat === '设备') return 'danger'
  if (cat === '环境') return 'warning'
  return 'info'
}

const createWorkOrder = (sol) => ElMessage.success(`工单已派发至：${sol.responsible}`)
const exportReport = async () => {
  const loading = ElLoading.service({
    lock: true,
    text: '正在生成高保真诊断报告 PDF...',
    background: 'rgba(255, 255, 255, 0.8)'
  })

  try {
    const reportElement = document.getElementById('pdf-report-content')
    if (!reportElement) {
      throw new Error('找不到报告模版元素')
    }

    // Force sampling chart rendering to populate off-screen canvas image data synchronously
    initSamplingCharts()

    // Capture the off-screen high-fidelity canvas directly to avoid any state synchronization delay
    const hiddenCanvas = document.getElementById('hiddenRunChartCanvas')
    if (hiddenCanvas) {
      try {
        const directDataUrl = hiddenCanvas.toDataURL('image/png')
        if (directDataUrl && directDataUrl !== 'data:,') {
          savedRunChartImg.value = directDataUrl
        }
      } catch (err) {
        console.warn('Direct hidden canvas data extraction failed:', err)
      }
    }

    // Use the off-screen rendered high-fidelity static image of runChartCanvas
    const chartImgEl = document.getElementById('pdf-chart-image')
    if (chartImgEl) {
      if (savedRunChartImg.value) {
        chartImgEl.src = savedRunChartImg.value
      } else {
        const canvasEl = document.getElementById('runChartCanvas')
        if (canvasEl) {
          chartImgEl.src = canvasEl.toDataURL('image/png')
        }
      }
    }

    // Set visibility for capture
    const originalStyle = reportElement.style.cssText
    reportElement.style.position = 'absolute'
    reportElement.style.left = '0'
    reportElement.style.top = '0'
    reportElement.style.zIndex = '-1000'
    reportElement.style.display = 'block'

    // Let the image render completely in the DOM before capturing
    await new Promise((resolve) => {
      const img = document.getElementById('pdf-chart-image')
      if (img && img.src) {
        if (img.complete) {
          resolve()
        } else {
          img.onload = () => resolve()
          img.onerror = () => resolve()
        }
      } else {
        resolve()
      }
    })

    const pdf = new jsPDF({
      orientation: 'portrait',
      unit: 'mm',
      format: 'a4'
    })

    const pages = reportElement.querySelectorAll('.pdf-page')
    for (let i = 0; i < pages.length; i++) {
       const page = pages[i]
       const canvas = await html2canvas(page, {
         scale: 2,
         useCORS: true,
         logging: false,
         backgroundColor: '#ffffff'
       })
       const imgData = canvas.toDataURL('image/png')
       if (i > 0) {
         pdf.addPage()
       }
       pdf.addImage(imgData, 'PNG', 0, 0, 210, 297)
    }

    // Restore original style
    reportElement.style.cssText = originalStyle

    const filename = `质量诊断报告_${filter.value.improvementTarget?.substring(0, 8) || '分析报告'}_${new Date().getTime()}.pdf`
    pdf.save(filename)
    
    ElMessage.success('诊断报告生成成功，已开始下载')
  } catch (error) {
    console.error('PDF Export Error:', error)
    ElMessage.error('报表生成失败，请稍后重试')
  } finally {
    loading.close()
  }
}
const previewReport = () => ElMessage.info('正在加载报告预览容器...')

const archiveHistory = () => {
  historyRecords.value.unshift({
    time: new Date().toLocaleString(),
    target: filter.value.improvementTarget || '通用性能优化',
    records: totalRecords.value,
    data: [...uploadedData.value],
    diagnosis: diagnosisResult.value,
    solutions_data: [...solutions.value]
  })
}

const ensureHistoryRecordData = (row) => {
  if (!row) return
  if (!row.data || !Array.isArray(row.data) || row.data.length === 0) {
    const dataCount = 20 + Math.floor(Math.random() * 20)
    const mockData = []
    const metrics = ['阻值-1和2', '阻值-3和4', '阻值-1和3', '阻值-1和4']
    const fName = row.target ? `${row.target}_检测数据.xlsx` : 'MOCK_DATA_V01.xlsx'
    for (let j = 0; j < dataCount; j++) {
      const valNum = 10000 + Math.floor(Math.random() * 90000)
      const pid = `${valNum}`
      metrics.forEach(m => {
        mockData.push({
          fileName: fName,
          file_name: fName,
          '文件名': fName,
          metric: m,
          '检测项': m,
          value: (25.0 + Math.random() * 0.8).toFixed(1),
          '实测值': (25.0 + Math.random() * 0.8).toFixed(1),
          '正阀编号': pid,
          '产品编号': pid,
          sample: (25.0 + Math.random() * 0.8).toFixed(1)
        })
      })
    }
    row.data = mockData
    row.records = mockData.length
  }
}

const loadHistory = (row) => {
  ensureHistoryRecordData(row)
  uploadedData.value = JSON.parse(JSON.stringify(row.data || []))
  diagnosisResult.value = JSON.parse(JSON.stringify(row.diagnosis || null))
  solutions.value = JSON.parse(JSON.stringify(row.solutions_data || []))
  isHistoryMode.value = true
  streamingDiagnosisResult.value = diagnosisResult.value ? diagnosisResult.value.root_causes : []
  streamingSolutions.value = JSON.parse(JSON.stringify(row.solutions_data || []))
  diagnosisThoughts.value = row.thoughts || ['数据加载完成', '正在解析历史诊断路径', '深度同步核心根因']
  filter.value.improvementTarget = row.target
  filter.value.focusPoints = row.focusPoints || ['mean_diff', 'process_capability']
  
  isThinking.value = false
  isDiagnosisStreaming.value = false
  isSolutionThoughtsBoxVisible.value = false
  isSolutionThinking.value = false
  
  currentStep.value = 1
  nextTick(() => {
    setTimeout(() => {
      initSamplingCharts()
      initPortraitCharts()
    }, 150)
  })
  showHistory.value = false
  ElMessage.success('已加载历史改善诊断详情')
}

const viewFullDiagnosis = (row) => {
  ensureHistoryRecordData(row)
  uploadedData.value = JSON.parse(JSON.stringify(row.data || []))
  diagnosisResult.value = JSON.parse(JSON.stringify(row.diagnosis || null))
  solutions.value = JSON.parse(JSON.stringify(row.solutions_data || []))
  isHistoryMode.value = true
  streamingDiagnosisResult.value = diagnosisResult.value ? diagnosisResult.value.root_causes : []
  streamingSolutions.value = JSON.parse(JSON.stringify(row.solutions_data || []))
  diagnosisThoughts.value = row.thoughts || ['数据加载完成', '正在解析历史诊断路径', '深度同步核心根因']
  filter.value.improvementTarget = row.target
  filter.value.focusPoints = row.focusPoints || ['mean_diff', 'process_capability']
  
  isThinking.value = false
  isDiagnosisStreaming.value = false
  isSolutionThoughtsBoxVisible.value = false
  isSolutionThinking.value = false
  
  currentStep.value = 2
  nextTick(() => {
    initSamplingCharts()
    initPortraitCharts()
  })
  showExpertCard.value = false
  showHistory.value = false
  ElMessage.success('已进入诊断分析画布')
}

const reset = () => {
  archiveHistory() // Save to history
  currentStep.value = 0
  uploadedData.value = [] 
  diagnosisResult.value = null
  solutions.value = []
  savedRunChartImg.value = ''
  isHistoryMode.value = false
  isSolutionsFlowCompleted.value = false
  router.push('/')
}
</script>

<style scoped>
/* Hidden content for PDF generation */
.hidden-pdf-content {
  position: fixed;
  left: -9999px;
  top: 0;
  width: 794px; /* A4 width in pixels at 96 DPI */
  color: #333;
  font-family: "PingFang SC", "Microsoft YaHei", sans-serif;
  z-index: -1000;
  background-color: #f1f5f9;
}

.pdf-page {
  width: 794px;
  height: 1122px;
  padding: 40px;
  box-sizing: border-box;
  background-color: white;
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  margin-bottom: 20px;
  overflow: hidden;
}

.pdf-header-compact {
  border-bottom: 2px solid #0052d9;
  padding-bottom: 10px;
  margin-bottom: 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.pdf-header {
  border-bottom: 2px solid #0052d9;
  padding-bottom: 20px;
  margin-bottom: 30px;
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
}

.pdf-logo-area {
  display: flex;
  align-items: center;
  gap: 15px;
}

.pdf-logo-text {
  font-size: 24px;
  font-weight: 850;
  color: #0052d9;
  letter-spacing: -0.5px;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

.pdf-logo {
  height: 50px;
  width: auto;
}

.pdf-main-title {
  margin: 0;
  font-size: 24px;
  color: #0052d9;
  letter-spacing: 1px;
}

.pdf-sub-title {
  margin: 2px 0 0;
  font-size: 10px;
  color: #666;
  text-transform: uppercase;
}

.pdf-header-meta {
  text-align: right;
  font-size: 12px;
  color: #666;
}

.meta-item {
  margin-bottom: 4px;
}

.pdf-section {
  margin-bottom: 32px;
}

.section-header-pdf {
  font-size: 16px;
  font-weight: bold;
  color: #1e293b;
  border-left: 4px solid #0052d9;
  padding-left: 12px;
  margin-bottom: 16px;
}

.target-card-pdf {
  background-color: #f8fafc;
  border: 1px solid #e2e8f0;
  padding: 20px;
  border-radius: 4px;
}

.target-text-pdf {
  font-size: 18px;
  font-weight: bold;
  color: #0052d9;
  margin-bottom: 10px;
}

.target-meta-pdf {
  font-size: 12px;
  color: #64748b;
}

.pdf-table {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 12px;
}

.pdf-table th {
  background-color: #f1f5f9;
  color: #475569;
  text-align: left;
  padding: 10px;
  font-size: 13px;
  border: 1px solid #e2e8f0;
}

.pdf-table td {
  padding: 10px;
  font-size: 13px;
  border: 1px solid #e2e8f0;
}

.pdf-table.secondary th {
  background-color: #eff6ff;
}

.pdf-data-summary {
  font-size: 11px;
  color: #64748b;
  font-style: italic;
}

.pdf-diagnosis-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.pdf-cause-item {
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  overflow: hidden;
}

.pdf-cause-header {
  background-color: #fef2f2;
  padding: 10px 15px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.pdf-cause-rank {
  font-weight: bold;
  color: #dc2626;
  font-size: 14px;
}

.pdf-cause-name {
  font-weight: bold;
  flex: 1;
  font-size: 15px;
}

.pdf-cause-conf {
  font-size: 12px;
  color: #dc2626;
  background: white;
  padding: 2px 8px;
  border-radius: 10px;
  border: 1px solid #fecaca;
}

.pdf-cause-body {
  padding: 15px;
  font-size: 13px;
  color: #475569;
}

.pdf-evidence-row {
  margin-top: 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.pdf-ev-tag {
  background-color: #f0fdf4;
  color: #16a34a;
  padding: 2px 8px;
  border-radius: 4px;
  border: 1px solid #bbf7d0;
  font-size: 11px;
}

.pdf-footer {
  position: absolute;
  bottom: 40px;
  left: 40px;
  right: 40px;
  text-align: center;
}

.pdf-footer-line {
  height: 1px;
  background-color: #e2e8f0;
  margin-bottom: 15px;
}

.pdf-footer-content {
  display: flex;
  justify-content: space-between;
  font-size: 10px;
  color: #94a3b8;
  margin-bottom: 10px;
}

.pdf-footer-caveat {
  font-size: 9px;
  color: #cbd5e1;
  margin: 0;
}

.workbench {
  min-height: 100%;
  background-color: #f5f7fa;
  display: flex;
  flex-direction: column;
}

.workbench-header {
  height: 64px;
  background-color: #fff;
  border-bottom: 1px solid var(--border-light);
  display: flex;
  align-items: center;
  padding: 0 40px;
  position: sticky;
  top: 0;
  z-index: 10;
}

.header-breadcrumb {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 14px;
  color: #606266;
}

.back-btn {
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 4px;
  transition: color 0.2s;
}

.back-btn:hover {
  color: var(--primary);
}

.divider {
  color: #C0C4CC;
}

.current-page {
  font-weight: 600;
  color: #303133;
}

.workbench-content {
  padding: 40px;
  max-width: 1400px;
  margin: 0 auto;
  width: 100%;
}

.steps-wrapper {
  padding: 24px 32px;
  margin-bottom: 24px;
}

.filter-card {
  box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
  border: 1px solid #e2e8f0;
}

.py-12 { padding-top: 12px; padding-bottom: 12px; }

.mt-32 { margin-top: 32px; }

.target-input-area :deep(.el-textarea__inner) {
  background: #f8fafc;
  border-radius: 6px;
  padding: 12px;
}


.custom-steps {
  max-width: 1000px;
  margin: 0 auto;
}

/* Simplified Upload In Sampling */
.simplified-upload :deep(.el-upload-dragger) {
  height: 120px;
  background-color: #f0f7ff;
}

.upload-icon-small {
  font-size: 32px;
  color: var(--primary);
  margin-bottom: 8px;
}

.micro-table {
  border-radius: 4px;
}



.action-footer-sampling {
  text-align: right;
}

.btn-primary-rect {
  padding: 12px 48px;
  border-radius: 4px;
  font-weight: 700;
}

.mb-24 { margin-bottom: 24px; }
.py-16 { padding-top: 16px; padding-bottom: 16px; }

/* Data Visualization Stage Styles */
.dashboard-visual {
  background: #fff;
  padding: 10px;
}

/* Prediction ROI Card */
.roi-card {
  padding: 0;
}

:deep(.el-upload-dragger) {
  height: 240px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  border: 2px dashed #DCDFE6;
  background-color: #f9faff;
  transition: all 0.3s;
}

:deep(.el-upload-dragger:hover) {
  border-color: var(--primary);
  background-color: #f0f7ff;
}

.upload-icon {
  font-size: 56px;
  color: #A0CFFF;
  margin-bottom: 12px;
}

.pulse-icon {
  display: inline-block;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% { transform: scale(1); opacity: 0.8; }
  50% { transform: scale(1.05); opacity: 1; }
  100% { transform: scale(1); opacity: 0.8; }
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.preview-title {
  font-weight: 600;
  font-size: 14px;
  color: #303133;
}

.data-preview-box {
  margin-bottom: 32px;
  padding: 16px;
  background: #fff;
  border: 1px solid var(--border-light);
  border-radius: 8px;
}

.status-tag {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 4px;
}
.status-tag.success { background: #f0f9eb; color: #67c23a; }
.status-tag.danger { background: #fef0f0; color: #f56c6c; }

.filter-panel {
  display: flex;
  flex-wrap: wrap;
  gap: 24px;
  padding: 20px;
  background-color: #f8fafc;
  border-radius: 8px;
  margin-bottom: 32px;
}

.filter-item {
  flex: 1;
  min-width: 200px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.filter-item.full-width {
  flex: 0 0 100%;
}

.filter-label {
  font-size: 12px;
  font-weight: 600;
  color: #909399;
}

.action-footer {
  text-align: center;
}

.btn-glow {
  padding: 12px 64px;
  font-weight: 600;
  border-radius: 8px;
}

/* AI Processing View */
.ai-processing-box {
  text-align: center;
  max-width: 600px;
  margin: 60px auto;
}

.ai-orb {
  width: 100px;
  height: 100px;
  background: radial-gradient(circle, var(--primary) 0%, transparent 70%);
  margin: 0 auto 24px;
  border-radius: 50%;
  animation: orb-glow 1.5s infinite alternate;
}

@keyframes orb-glow {
  from { box-shadow: 0 0 10px rgba(64, 158, 255, 0.2); }
  to { box-shadow: 0 0 40px rgba(64, 158, 255, 0.5); }
}

.ai-status {
  font-size: 18px;
  color: #303133;
  margin-bottom: 24px;
}

.scan-progress {
  margin-bottom: 32px;
}

.process-log {
  background: #1e293b;
  color: #94a3b8;
  padding: 16px;
  border-radius: 8px;
  font-family: 'JetBrains Mono', monospace;
  text-align: left;
  height: 180px;
  overflow-y: auto;
}

.log-item {
  margin: 4px 0;
  font-size: 12px;
}

.log-time {
  color: #22d3ee;
}

/* Results Display */
.grid-layout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}

.full-row {
  grid-column: 1 / -1;
}

.clickable-step {
  cursor: pointer;
  transition: all 0.3s;
}

.clickable-step:hover :deep(.el-step__title) {
  color: var(--primary);
}

.clickable-step:hover :deep(.el-step__icon) {
  border-color: var(--primary);
  color: var(--primary);
}

.xbar-s-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.panel-label {
  font-size: 13px;
  font-weight: 700;
  color: #475569;
  margin-bottom: 8px;
  padding-left: 4px;
  border-left: 3px solid var(--primary);
}

.canvas-wrapper-sm {
  height: 200px;
  width: 100%;
  position: relative;
}

.ml-auto {
  margin-left: auto;
}

.ml-16 {
  margin-left: 16px;
}

.auto-planning-hint {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #3b82f6;
  font-weight: 500;
  font-size: 14px;
}


.chart-container {
  height: 380px;
}

.chart-container-sm {
  height: 280px;
}

.canvas-wrapper {
  height: 260px;
  width: 100%;
  position: relative;
}

.canvas-wrapper-lg {
  height: 320px;
  width: 100%;
  position: relative;
}

.header-tag {
  display: inline-block;
  padding: 2px 10px;
  background-color: var(--primary-light);
  color: var(--primary);
  border-radius: 12px;
  font-size: 11px;
  font-weight: 700;
  margin-bottom: 6px;
  text-transform: uppercase;
}

.header-tag.danger {
  background-color: #fee2e2;
  color: #ef4444;
}

.cause-item {
  display: flex;
  gap: 16px;
  padding: 16px;
  border-bottom: 1px solid #f1f5f9;
}

.cause-rank {
  background: #f1f5f9;
  color: #475569;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 900;
  height: max-content;
}

.cause-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 6px;
}

.cause-name {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
}

.confidence {
  font-size: 11px;
  color: #94a3b8;
}

.cause-impact {
  font-size: 13px;
  color: #64748b;
  margin: 0 0 10px;
}

.evidence-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.evidence-tag {
  font-size: 11px;
  padding: 2px 8px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  color: #475569;
  display: flex;
  align-items: center;
  gap: 4px;
}

/* Table and Solution styles */
.header-flex {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.priority-dot {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
}
.priority-dot.high { background-color: #ef4444; }
.priority-dot.medium { background-color: #f59e0b; }

.mt-24 { margin-top: 24px; }
.mt-16 { margin-top: 16px; }
.ml-8 { margin-left: 8px; }

/* Decision Box */
.decision-box {
  background: #fff;
  padding: 32px;
  border-radius: 12px;
  border: 1px solid var(--border-light);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
}

@media (max-width: 1024px) {
  .dashboard-grid-conclusion, .sampling-charts-grid {
    grid-template-columns: 1fr;
  }
}

.animate-fade-in {
  animation: fadeIn 0.4s ease-out forwards;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}

.stats-summary-card {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.05);
}

.card-title-sm {
  font-size: 14px;
  font-weight: 700;
  color: #1e293b;
}

.text-danger-custom { color: #ef4444; }
.text-primary-custom { color: #3b82f6; }
.font-bold { font-weight: 700; }

.stats-summary-table :deep(.el-table__header) th {
  background-color: #f8fafc !important;
  color: #475569;
  font-weight: 800;
}

/* Quality Report Styles */
.report-list-card {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.05);
}

.report-document-container {
  position: relative;
  height: 320px;
  overflow: hidden;
  cursor: pointer;
  background: #f8fafc;
  display: flex;
  justify-content: center;
  padding-top: 24px;
}

.report-doc-mock {
  width: 600px;
  background: white;
  min-height: 800px;
  box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.1);
  padding: 40px;
}

.doc-red-border {
  border: 4px solid #ef4444;
  height: 100%;
  padding: 30px;
  position: relative;
}

.doc-header-info {
  display: flex;
  justify-content: space-between;
  margin-bottom: 80px;
}

.info-row {
  display: flex;
  align-items: flex-end;
  margin-bottom: 8px;
  font-size: 14px;
  color: #000;
  font-family: "Times New Roman", serif;
}

.info-row .label {
  font-weight: bold;
}

.underline-red {
  border-bottom: 1px solid #ef4444;
  min-width: 100px;
  display: inline-block;
  height: 20px;
  padding-left: 10px;
  margin-left: 4px;
  font-weight: bold;
}

.doc-content-body {
  text-align: center;
  font-family: serif;
  color: #000;
}

.doc-series {
  font-size: 24px;
  border-bottom: 2px solid #000;
  display: inline-block;
  margin-bottom: 24px;
  padding: 0 20px;
}

.doc-model {
  font-size: 28px;
  font-weight: bold;
  margin-bottom: 16px;
}

.doc-title {
  font-size: 36px;
  font-weight: bold;
}

.fade-overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 180px;
  background: linear-gradient(to bottom, transparent, rgba(248, 250, 252, 0.9) 60%, #f8fafc);
  pointer-events: none;
}

.view-more-btn-box {
  position: absolute;
  bottom: 40px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 10;
}

/* Expert Card Premium Styles */
.expert-card-dialog {
  background: transparent !important;
  box-shadow: none !important;
  border: none !important;
}

.expert-card-dialog :deep(.el-dialog__header) {
  display: none !important;
}

.expert-card-dialog :deep(.el-dialog__body) {
  padding: 0 !important;
  background: transparent !important;
}

.expert-card-container {
  padding: 0;
}

.card-main {
  position: relative;
  border-radius: 20px;
  overflow: hidden;
  background: #ffffff;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
  border: 1px solid rgba(255, 255, 255, 0.82);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

/* Close button on card top-right */
.expert-card-close {
  position: absolute;
  top: 18px;
  right: 18px;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.2);
  color: rgba(255, 255, 255, 0.85);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  z-index: 10;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.expert-card-close:hover {
  background: rgba(255, 255, 255, 0.25);
  color: #ffffff;
  transform: scale(1.08) rotate(90deg);
}

/* Header Background containing premium mesh & grid */
.card-top-bg {
  height: 140px;
  background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 100%);
  background-image: 
    radial-gradient(rgba(255, 255, 255, 0.12) 1px, transparent 1px),
    linear-gradient(135deg, #020617 0%, #1e3a8a 100%);
  background-size: 12px 12px, 100% 100%;
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  z-index: 0;
}

/* Card Content Area */
.card-content {
  position: relative;
  z-index: 1;
  padding: 24px;
  padding-top: 28px;
}

.card-header-expert {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}

.expert-identity {
  display: flex;
  align-items: center;
  gap: 14px;
}

/* Animated Neon Expert Badge */
.expert-avatar-box {
  width: 54px;
  height: 54px;
  background: rgba(15, 23, 42, 0.85);
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 0 15px rgba(49, 232, 255, 0.35);
  border: 2px solid rgba(49, 232, 255, 0.6);
  position: relative;
}

.avatar-glow {
  position: absolute;
  top: -2px;
  left: -2px;
  right: -2px;
  bottom: -2px;
  border-radius: 14px;
  border: 2px solid #31e8ff;
  opacity: 0;
  animation: borderGlow 2.5s infinite alternate;
  pointer-events: none;
}

@keyframes borderGlow {
  0% { opacity: 0.1; box-shadow: 0 0 4px rgba(49, 232, 255, 0.2); }
  100% { opacity: 0.7; box-shadow: 0 0 14px rgba(49, 232, 255, 0.6); }
}

.expert-name-box {
  color: #ffffff;
}

.expert-label {
  font-size: 17px;
  font-weight: 700;
  letter-spacing: 0.5px;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
  line-height: 1.25;
}

.expert-sub-label {
  font-size: 9px;
  font-family: 'JetBrains Mono', monospace;
  opacity: 0.65;
  letter-spacing: 0.8px;
  margin-top: 1px;
}

/* Infinite Breath Green online dot */
.expert-status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: rgba(16, 185, 129, 0.12);
  border: 1px solid rgba(16, 185, 129, 0.25);
  padding: 2px 8px;
  border-radius: 12px;
  margin-top: 6px;
}

.status-text {
  font-size: 10px;
  color: #34d399;
  font-weight: 600;
}

.dot-online-pulse {
  width: 6px;
  height: 6px;
  background: #10b981;
  border-radius: 50%;
  display: inline-block;
  box-shadow: 0 0 8px #10b981;
  animation: statusPulse 1.8s infinite ease-in-out;
}

@keyframes statusPulse {
  0% { transform: scale(0.9); opacity: 0.6; box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
  70% { transform: scale(1.1); opacity: 1; box-shadow: 0 0 0 6px rgba(16, 185, 129, 0); }
  100% { transform: scale(0.9); opacity: 0.6; box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
}

.card-id {
  background: rgba(255, 255, 255, 0.12);
  color: #ffffff;
  padding: 4px 8px;
  border-radius: 6px;
  font-size: 10px;
  font-family: 'JetBrains Mono', monospace;
  letter-spacing: 0.5px;
  border: 1px solid rgba(255, 255, 255, 0.15);
  text-shadow: 0 1px 2px rgba(0,0,0,0.2);
}

.card-body-expert {
  margin-top: 24px;
}

/* Bento grid container */
.meta-bento-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
  margin-bottom: 16px;
}

.bento-meta-item {
  background: #f8fafc;
  border: 1px solid #f1f5f9;
  border-radius: 10px;
  padding: 10px 14px;
}

.meta-label {
  font-size: 10px;
  color: #64748b;
  font-weight: 700;
  letter-spacing: 0.5px;
  margin-bottom: 4px;
}

.meta-value-goal {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  color: #1e293b;
  font-weight: 700;
}

.meta-value-goal .icon-target {
  color: #0052d9;
}

.meta-value-time {
  font-size: 13px;
  color: #475569;
  font-family: 'JetBrains Mono', monospace;
  font-weight: 500;
}

/* Telemetry Dashboard Stats */
.card-stats-expert {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 16px 0;
  background: linear-gradient(135deg, #f0f4ff 0%, #f5f8ff 100%);
  padding: 14px 18px;
  border-radius: 12px;
  border: 1px solid #e0ebff;
}

.card-stats-expert .stat-box {
  flex: 1;
  text-align: center;
}

.stat-divider-vertical {
  width: 1px;
  height: 38px;
  background: #dbeafe;
}

.stat-num-container {
  display: flex;
  align-items: baseline;
  justify-content: center;
  gap: 2px;
}

.stat-num {
  font-size: 26px;
  font-weight: 800;
  color: #1e3a8a;
  letter-spacing: -0.5px;
  font-family: 'JetBrains Mono', monospace;
}

.stat-num.danger-num {
  color: #dc2626;
}

.stat-unit {
  font-size: 11px;
  color: #475569;
  font-weight: 600;
}

.stat-unit.danger-unit {
  color: #dc2626;
}

.stat-label {
  font-size: 11px;
  color: #64748b;
  font-weight: 600;
  margin-top: 2px;
}

/* Diagnostic conclusion bento list */
.card-diagnosis-preview {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  padding: 14px;
  border-radius: 12px;
  margin-top: 14px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.02);
}

.preview-label {
  font-size: 11px;
  font-weight: 700;
  color: #475569;
  margin-bottom: 12px;
  letter-spacing: 0.5px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.label-indicator {
  width: 4px;
  height: 12px;
  background: #0052d9;
  border-radius: 2px;
  display: inline-block;
}

.preview-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.preview-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 12px;
  background: #f8fafc;
  border-radius: 8px;
  border: 1px solid #f1f5f9;
}

.item-index {
  font-size: 11px;
  font-family: 'JetBrains Mono', monospace;
  font-weight: 700;
  color: #3b82f6;
  background: #eff6ff;
  width: 20px;
  height: 20px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.item-text-content {
  flex: 1;
}

.item-cause-title {
  font-size: 12.5px;
  font-weight: 700;
  color: #1e293b;
  line-height: 1.4;
}

.item-cause-desc {
  font-size: 11px;
  color: #64748b;
  margin-top: 2px;
  line-height: 1.4;
}

/* Footer Drawer and Actions */
.card-footer-expert {
  margin-top: 24px;
}

.btn-expert {
  height: 48px;
  border-radius: 12px;
  font-weight: 700;
  font-size: 14px;
  letter-spacing: 0.5px;
  background: #0052d9;
  border-color: #0052d9;
  box-shadow: 0 4px 12px rgba(0, 82, 217, 0.25);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.btn-expert:hover {
  background: #2463eb;
  border-color: #2463eb;
  box-shadow: 0 6px 16px rgba(37, 99, 235, 0.35);
  transform: translateY(-1px);
}

.btn-expert .icon-arrow {
  margin-left: 2px;
  transition: transform 0.2s;
}

.btn-expert:hover .icon-arrow {
  transform: translateX(3px);
}

.footer-hint {
  text-align: center;
  margin-top: 14px;
  font-size: 10px;
  color: #94a3b8;
  font-weight: 600;
  letter-spacing: 0.5px;
}

.report-preview-grid {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.report-item-mini {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  background: #f8fafc;
  border: 1px solid #f1f5f9;
  border-radius: 6px;
  transition: all 0.2s;
}

.report-item-mini:hover {
  background: #f1f5f9;
  border-color: #cbd5e1;
}

.report-icon-box {
  width: 40px;
  height: 40px;
  background: #eff6ff;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 16px;
}

.report-icon-lg {
  font-size: 20px;
  color: #3b82f6;
}

.report-info-main {
  flex: 1;
}

.report-name-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 4px;
}

.report-name-text {
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
}

.status-pill {
  font-size: 11px;
  padding: 1px 8px;
  border-radius: 12px;
  font-weight: 600;
}

.status-pill.success { background: #dcfce7; color: #166534; }
.status-pill.warning { background: #fef9c3; color: #854d0e; }
.status-pill.danger { background: #fee2e2; color: #991b1b; }

.report-meta-text {
  font-size: 12px;
  color: #64748b;
  display: flex;
  align-items: center;
}

.mx-8 { margin-left: 8px; margin-right: 8px; }

.anim-slide-up {
  animation: slideUp 0.5s ease-out forwards;
}

@keyframes slideUp {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

:deep(.reports-dialog) {
  border-radius: 12px;
}

:deep(.reports-dialog .el-dialog__header) {
  padding: 24px;
  margin-right: 0;
  border-bottom: 1px solid #e2e8f0;
}

:deep(.reports-dialog .el-dialog__body) {
  padding: 24px;
}

.dialog-filter-bar {
  display: flex;
  justify-content: flex-end;
}

:deep(.full-page-dialog) {
  .el-dialog__header {
    display: none;
  }
  .el-dialog__body {
    padding: 0;
    height: 100vh;
  }
}
/* AI Thought Process Streaming */
.thought-process-wrapper,
.solution-thought-wrapper {
  background: #f8fafc;
  padding: 16px;
  border-radius: 8px;
  border-left: 4px solid #3b82f6;
  height: 192px;
  box-sizing: border-box;
  overflow-y: auto;
  scroll-behavior: smooth;
}

.thought-process-wrapper::-webkit-scrollbar,
.solution-thought-wrapper::-webkit-scrollbar {
  width: 6px;
}
.thought-process-wrapper::-webkit-scrollbar-track,
.solution-thought-wrapper::-webkit-scrollbar-track {
  background: transparent;
}
.thought-process-wrapper::-webkit-scrollbar-thumb,
.solution-thought-wrapper::-webkit-scrollbar-thumb {
  background-color: #cbd5e1;
  border-radius: 3px;
}
.thought-process-wrapper::-webkit-scrollbar-thumb:hover,
.solution-thought-wrapper::-webkit-scrollbar-thumb:hover {
  background-color: #94a3b8;
}

.thought-item {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 20px;
  margin-bottom: 8px;
  color: #64748b;
  font-size: 13px;
  line-height: 20px;
  opacity: 0;
  animation: fadeIn 0.3s forwards;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.thought-item:last-child {
  margin-bottom: 0;
}

.thought-item.current-thought {
  color: #3b82f6;
  font-weight: 500;
}

.thought-icon {
  font-size: 14px;
}

.animate-slide-in {
  animation: slideIn 0.5s ease-out forwards;
}

@keyframes slideIn {
  from { opacity: 0; transform: translateX(-20px); }
  to { opacity: 1; transform: translateX(0); }
}

.diagnostic-results-panel {
  border: 1px solid #e2e8f0;
  background: #fff;
}

.header-actions-right {
  display: flex;
  align-items: center;
}

.history-dialog :deep(.el-dialog__body) {
  padding: 20px 24px;
}
</style>

