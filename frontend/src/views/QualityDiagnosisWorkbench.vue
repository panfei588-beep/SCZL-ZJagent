<template>
  <div class="workbench">
    <div class="workbench-header">
      <div class="header-breadcrumb">
        <span class="back-btn" @click="goBack">
          <el-icon><ArrowLeft /></el-icon> 返回
        </span>
        <span class="divider">/</span>
        <span class="current-page">质量异常诊断工作台</span>
      </div>
    </div>

    <div class="workbench-content">
      <!-- Steps Navigation -->
      <div class="steps-wrapper card">
        <el-steps :active="currentStep" align-center class="custom-steps">
          <el-step title="数据采样" :icon="Upload" />
          <el-step title="AI 根因诊断" :icon="Cpu" />
          <el-step title="多维结果画像" :icon="PieChart" />
          <el-step title="智能化改进方案" :icon="CircleCheck" />
          <el-step title="方案验证与归因" :icon="Odometer" />
          <el-step title="双样本 T-test" :icon="PieChart" />
          <el-step title="固本方案 SOP" :icon="Management" />
        </el-steps>
      </div>

      <!-- Step 0: Upload -->
      <div v-if="currentStep === 0" class="step-container animate-fade-in">
        <div class="card upload-card">
          <div class="card-header">
            <h3 class="section-title">Step 1: 上传质量检测数据</h3>
          </div>
          <div class="card-body">
            <el-upload
              class="upload-area"
              drag
              action="#"
              :auto-upload="false"
              :on-change="handleFileChange"
              :on-remove="handleFileRemove"
              :file-list="fileList"
              multiple
            >
              <div class="upload-inner">
                <div class="pulse-icon">
                  <el-icon class="upload-icon"><UploadFilled /></el-icon>
                </div>
                <div class="el-upload__text">
                  将质量报表拖拽到此处，或 <em>点击上传</em>
                </div>
                <div class="upload-hint">支持 Excel, PDF, CSV, Word 格式，支持同时上传多个文件，单个文件不超过 50MB</div>
              </div>
            </el-upload>

            <!-- Data Preview if uploaded -->
            <div v-if="uploadedData.length > 0" class="data-preview-box animate-fade-in">
              <div class="preview-header">
                <span class="preview-title">数据预览 (前5条)</span>
                <el-tag type="success" size="small">已识别 {{ totalRecords }} 条记录</el-tag>
              </div>
              <el-table :data="uploadedData.slice(0, 5)" border stripe size="small" class="mini-table">
                <el-table-column prop="日期" label="日期" width="100" />
                <el-table-column prop="产品编号" label="产品" width="100" />
                <el-table-column prop="检测项" label="检测项" />
                <el-table-column prop="实测值" label="实测值" width="80" />
                <el-table-column prop="判定" label="判定" width="80">
                  <template #default="scope">
                    <span :class="['status-tag', scope.row.判定 === '合格' ? 'success' : 'danger']">{{ scope.row.判定 }}</span>
                  </template>
                </el-table-column>
              </el-table>
            </div>

            <!-- Warning Banner -->
            <div v-if="uploadWarning" class="warning-banner-box animate-fade-in">
              <el-alert
                :title="uploadWarning"
                type="warning"
                :closable="true"
                show-icon
                @close="uploadWarning = ''"
              />
            </div>

            <div class="filter-panel">
              <div class="filter-item">
                <span class="filter-label">生产设备</span>
                <el-select v-model="filter.device" placeholder="选择设备" class="custom-select">
                  <el-option label="3号精密磨床" value="3_grinder" />
                  <el-option label="5号CNC加工中心" value="5_cnc" />
                </el-select>
              </div>
              <div class="filter-item">
                <span class="filter-label">时间维度</span>
                <el-select v-model="filter.timeRange" placeholder="选择时间" class="custom-select">
                  <el-option label="最近24小时" value="24h" />
                  <el-option label="最近7天" value="7d" />
                  <el-option label="自定义" value="custom" />
                </el-select>
              </div>
              <div class="filter-item">
                <span class="filter-label">操作人</span>
                <el-select v-model="filter.operator" placeholder="全部" class="custom-select">
                  <el-option label="张伟" value="张伟" />
                  <el-option label="李四" value="李四" />
                </el-select>
              </div>
            </div>

            <!-- Diagnosis Config Panel -->
            <el-collapse v-model="activeConfigCollapse" class="config-collapse" v-show="filePaths.length > 0">
              <el-collapse-item title="诊断配置" name="config">
                <div class="config-panel">
                  <div class="config-section">
                    <label class="config-section-title">关注指标</label>
                    <el-checkbox-group v-model="diagnosisConfig.focusMetrics">
                      <el-checkbox label="合格率" />
                      <el-checkbox label="尺寸偏差" />
                      <el-checkbox label="表面粗糙度" />
                      <el-checkbox label="圆度" />
                      <el-checkbox label="波纹度" />
                    </el-checkbox-group>
                  </div>
                  <div class="config-section">
                    <label class="config-section-title">分析目标</label>
                    <el-radio-group v-model="diagnosisConfig.analysisGoal">
                      <el-radio label="root_cause">根因定位</el-radio>
                      <el-radio label="trend_prediction">趋势预测</el-radio>
                      <el-radio label="comprehensive_diagnosis">全面诊断</el-radio>
                    </el-radio-group>
                  </div>
                  <div class="config-section">
                    <label class="config-section-title">诊断深度</label>
                    <div class="slider-row">
                      <el-slider v-model="diagnosisConfig.depth" :min="1" :max="5" :marks="{ 1: '浅层', 3: '标准', 5: '深层' }" show-stops />
                      <span class="slider-value">{{ diagnosisConfig.depth }}</span>
                    </div>
                  </div>
                </div>
              </el-collapse-item>
            </el-collapse>

            <div class="action-footer">
              <el-button type="primary" size="large" class="btn-glow" :loading="loading" @click="startAIScan">
                开始智能化诊断
              </el-button>
            </div>
          </div>
        </div>
      </div>

      <!-- Step 1: AI Analyzing -->
      <div v-if="currentStep === 1" class="step-container diagnostic-loading animate-fade-in">
        <div class="ai-processing-box">
          <div class="ai-orb"></div>
          <h2 class="ai-status">专注于质量波动特征解析中...</h2>
          <el-progress :percentage="scanProgress" :stroke-width="8" class="scan-progress" />
          <div class="process-log">
            <p v-for="(log, index) in diagnosticLogs" :key="index" class="log-item">
              <span class="log-time">[{{ log.time }}]</span> {{ log.msg }}
            </p>
          </div>
        </div>
      </div>

      <!-- Step 2: Result View -->
      <div v-if="currentStep === 2" class="step-container animate-fade-in">
        <!-- Low Confidence Warning -->
        <div v-if="diagnosisResult?.low_confidence_warning" class="mb-16">
          <el-alert
            title="本次诊断置信度较低，结果仅供参考"
            type="warning"
            show-icon
            :closable="false"
          />
        </div>

        <!-- Charts Section -->
        <div v-if="diagnosisResult?.charts && diagnosisResult.charts.length > 0" class="charts-section mb-16 card">
          <div class="card-header">
            <span class="header-tag">可视化分析</span>
            <h3 class="card-title">AI 诊断图表</h3>
          </div>
          <div class="card-body charts-grid">
            <div v-for="(chart, idx) in diagnosisResult.charts" :key="idx" class="chart-image-wrapper">
              <img :src="chart.startsWith('/') ? chart : `/api/static/charts/${chart}`" :alt="`诊断图表 ${idx + 1}`" class="chart-image" />
            </div>
          </div>
        </div>

        <!-- Statistics Table -->
        <div v-if="diagnosisResult?.statistics && diagnosisResult.statistics.length > 0" class="statistics-section mb-16 card">
          <div class="card-header">
            <span class="header-tag">数据概览</span>
            <h3 class="card-title">关键统计指标</h3>
          </div>
          <div class="card-body">
            <el-table :data="diagnosisResult.statistics" border stripe class="custom-table">
              <el-table-column prop="metric" label="指标" width="120" />
              <el-table-column prop="max" label="最大值" width="100" />
              <el-table-column prop="min" label="最小值" width="100" />
              <el-table-column prop="mean" label="均值" width="100" />
              <el-table-column prop="std" label="标准差" width="100" />
              <el-table-column prop="envelope" label="波动包络" />
            </el-table>
          </div>
        </div>

        <div class="grid-layout">
          <!-- Left: Quality Trend -->
          <div class="card chart-card">
            <div class="card-header">
              <span class="header-tag">指标监控</span>
              <h3 class="card-title">质量合格率波动趋势</h3>
            </div>
            <div class="card-body">
              <div id="trendChart" class="chart-container"></div>
            </div>
          </div>

          <!-- Right: Root Causes -->
          <div class="card causes-card">
            <div class="card-header">
              <span class="header-tag danger">核心根因</span>
              <h3 class="card-title">AI 推理异常链路对齐</h3>
            </div>
            <div class="card-body">
              <div v-for="cause in diagnosisResult.root_causes" :key="cause.rank" class="cause-item">
                <div class="cause-rank">NO.{{ cause.rank }}</div>
                <div class="cause-info">
                  <div class="cause-title-row">
                    <h4 class="cause-name">{{ cause.cause }}</h4>
                    <el-tag :type="getTagType(cause.category)" size="small" effect="dark">{{ cause.category }}</el-tag>
                    <span class="confidence">置信度: {{ (cause.confidence * 100).toFixed(0) }}%</span>
                  </div>
                  <p class="cause-impact">{{ cause.impact }}</p>
                  <div class="evidence-list">
                    <div v-for="(ev, idx) in cause.evidence" :key="idx" class="evidence-tag">
                      <el-icon><Check /></el-icon> {{ ev }}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="action-footer mt-24">
          <el-button size="large" @click="currentStep = 0">重置诊断</el-button>
          <el-button type="primary" size="large" @click="handleGenerateSolutions">生成针对性改进方案</el-button>
        </div>
      </div>

      <!-- Step 3: Solutions -->
      <div v-if="currentStep === 3" class="step-container animate-fade-in">
        <div class="card solution-card">
          <div class="card-header header-flex">
            <h3 class="card-title">智能化质量体系改进规划</h3>
            <div class="header-actions">
              <el-button type="info" plain class="btn-sm" @click="previewReport">
                <el-icon><View /></el-icon> 报告预览
              </el-button>
              <el-button type="primary" plain class="btn-sm" @click="exportReport">
                <el-icon><Download /></el-icon> 下载诊断报告
              </el-button>
            </div>
          </div>
          <div class="card-body">
            <el-table :data="solutions" class="custom-table" border stripe>
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
              <el-table-column label="决策" width="160">
                <template #default="scope">
                  <el-button type="primary" link @click="createWorkOrder(scope.row)">指派工单</el-button>
                  <el-button type="warning" link @click="openFeedbackDialog(scope.row)">试验反馈</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
          <div class="card-footer text-center">
            <el-button type="primary" size="large" @click="currentStep = 4; nextTick(() => initVerificationCharts())">进入归因验证分析</el-button>
            <el-button size="large" @click="reset">归档并返回</el-button>
          </div>
        </div>

        <el-dialog v-model="feedbackVisible" title="改进方案试验反馈" width="500px" append-to-body>
          <el-form :model="feedbackForm" label-width="100px">
            <el-form-item label="改进项">
              <el-input v-model="feedbackForm.action" disabled />
            </el-form-item>
            <el-form-item label="试验状态">
              <el-radio-group v-model="feedbackForm.status">
                <el-radio label="已完成">执行完毕</el-radio>
                <el-radio label="试验中">持续观察</el-radio>
              </el-radio-group>
            </el-form-item>
            <el-form-item label="试验结果">
              <el-input 
                type="textarea" 
                v-model="feedbackForm.result" 
                placeholder="请输入试验后的质量表现、数值提升等关键结论"
                :rows="3"
              />
            </el-form-item>
            <el-form-item label="合格率提升">
              <el-input-number v-model="feedbackForm.improvement" :precision="2" :step="0.1" :max="100" />
              <span class="ml-8">%</span>
            </el-form-item>
          </el-form>
          <template #footer>
            <el-button @click="feedbackVisible = false">取消</el-button>
            <el-button type="primary" @click="submitFeedback">提交反馈数据</el-button>
          </template>
        </el-dialog>

        <!-- New: Multidimensional Portrait Charts -->
        <div class="grid-layout mt-24">
          <div class="card chart-card">
            <div class="card-header">
              <span class="header-tag">体系对齐</span>
              <h3 class="card-title">6M 多维质量成熟度画像</h3>
            </div>
            <div class="card-body">
              <div id="radarChart" class="chart-container-sm"></div>
            </div>
          </div>
          <div class="card predictor-card">
            <div class="card-header">
              <span class="header-tag">效益预估</span>
              <h3 class="card-title">方案实施预期 ROI 预测</h3>
            </div>
            <div class="card-body">
              <div id="predictorChart" class="chart-container-sm"></div>
            </div>
          </div>
        </div>
      </div>

      <!-- Step 4: Attribution Analysis -->
      <div v-if="currentStep === 4" class="step-container animate-fade-in">
        <div class="grid-layout">
          <!-- Verification Chart -->
          <div class="card chart-card">
            <div class="card-header">
              <span class="header-tag">方案验证</span>
              <h3 class="card-title">改进前后质量指标对比 (Before vs After)</h3>
            </div>
            <div class="card-body">
              <div id="verificationChart" class="chart-container"></div>
            </div>
          </div>

          <!-- Attribution Analysis -->
          <div class="card attribution-card">
            <div class="card-header">
              <span class="header-tag">深度归因</span>
              <h3 class="card-title">AI 效能归因与闭环分析</h3>
            </div>
            <div class="card-body">
              <div class="attribution-content">
                <div class="summary-stat">
                  <div class="stat-item">
                    <span class="label">平均良率提升</span>
                    <span class="value text-success">+{{ avgImprovement }}%</span>
                  </div>
                  <div class="stat-item">
                    <span class="label">风险消除率</span>
                    <span class="value text-primary">94.2%</span>
                  </div>
                </div>

                <div class="logic-flow">
                  <h4 class="sub-title">AI 归因逻辑链条</h4>
                  <el-timeline>
                    <el-timeline-item timestamp="逻辑验证" type="primary" :icon="Cpu">
                      <p class="logic-desc">诊断定位的“3号磨床砂轮振动”在采取“动态主轴动平衡补偿”后，异常谐波幅值下降 82.5%。</p>
                    </el-timeline-item>
                    <el-timeline-item timestamp="因果关联" type="success" :icon="Connection">
                      <p class="logic-desc">试验数据反馈显示，工件表面粗糙度合格率由 89% 提升至 97.4%，与改进方案具有极强因果正相关。</p>
                    </el-timeline-item>
                    <el-timeline-item timestamp="结论闭环" type="info" :icon="CircleCheck">
                      <p class="logic-desc">质量波动已受控，建议将此改进参数沉淀至 SOP 知识库，作为标准化工艺基准。</p>
                    </el-timeline-item>
                  </el-timeline>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="action-footer mt-24 decision-box">
          <div class="decision-label">根据试验效果决策下一步：</div>
          <div class="decision-btns">
            <el-button @click="currentStep = 3">重新分析改进方案</el-button>
            <el-button type="primary" size="large" class="btn-glow" @click="currentStep = 5">
              采纳改进方案并进入 T-test 验证
            </el-button>
          </div>
        </div>
      </div>

      <!-- Step 5: Two-sample T-test -->
      <div v-if="currentStep === 5" class="step-container animate-fade-in">
        <div class="card ttest-card">
          <div class="card-header">
            <span class="header-tag">统计推断</span>
            <h3 class="card-title">双样本 T-test 效应显著性分析</h3>
          </div>
          <div class="card-body">
            <div class="ttest-layout">
              <!-- Data Import Section -->
              <div class="ttest-upload-section">
                <div class="upload-title">上传后续实际生产检测数据</div>
                <el-upload
                  class="mini-upload"
                  drag
                  action="#"
                  :auto-upload="false"
                  :on-change="handleTtestFileChange"
                >
                  <el-icon class="el-icon--upload"><Upload /></el-icon>
                  <div class="el-upload__text">拖拽或点击上传验证数据</div>
                </el-upload>
                
                <div v-if="ttestDataUploaded" class="validation-status success animate-fade-in">
                  <el-icon><CircleCheck /></el-icon> 已识别 128 条后续生产记录
                </div>
              </div>

              <!-- Metrics Comparison -->
              <div class="ttest-results-section" v-if="ttestDataUploaded">
                <div class="grid-layout">
                  <div class="chart-box">
                    <div id="distributionChart" class="chart-container-sm"></div>
                  </div>
                  <div class="stats-summary">
                    <h4 class="sub-title">统计学指标分析结论</h4>
                    <div class="metric-grid">
                      <div class="metric-card">
                        <span class="label">P-Value (显著性)</span>
                        <span class="value text-success">0.024</span>
                        <span class="hint">小于 0.05，改善具有统计学意义</span>
                      </div>
                      <div class="metric-card">
                        <span class="label">效应量 (Cohen's d)</span>
                        <span class="value text-primary">0.82</span>
                        <span class="hint">大效应量</span>
                      </div>
                      <div class="metric-card">
                        <span class="label">置信区间 (95% CI)</span>
                        <span class="value text-dark">[1.2%, 4.5%]</span>
                        <span class="hint">指标提升的稳态区间</span>
                      </div>
                    </div>
                    
                    <div class="conclusion-box mt-16">
                      <el-alert
                        title="AI 终审建议：全面实施工艺改进"
                        type="success"
                        description="基于双样本 T-test 验证，当前改进方案对良率提升具有显著正相关作用。建议进入标准化作业 (SOP) 流程，并建议在全线推广。"
                        show-icon
                        :closable="false"
                      />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div class="card-footer text-center mt-24">
            <el-button @click="currentStep = 4">重新分析数据</el-button>
            <el-button type="primary" size="large" class="btn-glow" @click="goToSOP">
              生成质量改进固本方案 (SOP)
            </el-button>
          </div>
        </div>
      </div>

      <!-- Step 6: Solidified SOP & Dashboard -->
      <div v-if="currentStep === 6" class="step-container animate-fade-in dashboard-mode">
        <!-- Role Selector -->
        <div class="role-selector card">
          <div class="selector-label">切换视图角色：</div>
          <el-radio-group v-model="activeRole" class="custom-radio">
            <el-radio-button label="manager">车间主任</el-radio-button>
            <el-radio-button label="qc">质检工程师</el-radio-button>
            <el-radio-button label="process">工艺工程师</el-radio-button>
          </el-radio-group>
        </div>

        <div class="dashboard-grid">
          <!-- Left: SOP Document -->
          <div class="card sop-document">
            <div class="card-header header-flex">
              <h3 class="card-title"><el-icon><Management /></el-icon> 标准化作业 (SOP) 固本方案</h3>
              <div class="header-actions">
                <el-button type="primary" link @click="archiveSop">方案存档</el-button>
                <el-button type="primary" link @click="downloadWord"><el-icon><Download /></el-icon> 下载 Word 版</el-button>
              </div>
            </div>
            <div class="card-body scrollable-content">
              <div class="sop-content">
                <section class="sop-section">
                  <h4 class="sop-title">1. 背景与目标</h4>
                  <p>针对 3号精密磨床 出现的表面粗糙度周期性超差问题（异常码：ERR-2024-0032），通过 AI 进行根因分析与验证，本方案旨在将成功的改进措施固化，防止波动再次发生。</p>
                </section>
                <section class="sop-section">
                  <h4 class="sop-title">2. 核心改进措施</h4>
                  <div class="sop-table-wrapper">
                    <table class="sop-mini-table">
                      <thead>
                        <tr><th>维度</th><th>原作业参数</th><th>固化后标准 (SOP)</th></tr>
                      </thead>
                      <tbody>
                        <tr><td>主轴频率</td><td>50Hz 固定</td><td>动态闭环补频 (48.5Hz-51.2Hz)</td></tr>
                        <tr><td>进给量</td><td>0.05mm/s</td><td>0.042mm/s (精度优先级)</td></tr>
                        <tr><td>冷却液压力</td><td>0.2MPa</td><td>恒压 0.28MPa ±0.01</td></tr>
                      </tbody>
                    </table>
                  </div>
                </section>
                <section class="sop-section">
                  <h4 class="sop-title">3. 监测与闭环</h4>
                  <p>每日 8:00 执行 X-bar 控制图点检，若连续 3 点处于 C 区偏上，立即启动 AI 预警并执行自动补正程序。</p>
                </section>
              </div>
              <div class="sop-footer mt-16">
                 <el-button type="info" plain block @click="currentStep = 3">重新生成方案</el-button>
              </div>
            </div>
          </div>

          <!-- Right: Reporting Dashboard -->
          <div class="report-view">
            <!-- Manager View: Highlights, Pareto, Quality Comparison -->
            <div v-show="activeRole === 'manager'" class="role-view animate-fade-in">
              <div class="report-row">
                <div class="card stat-card">
                  <div class="card-body">
                    <div class="stat-main">
                      <span class="label">综合达成率</span>
                      <span class="value">98.4%</span>
                      <el-tag type="success">↑ 9.4%</el-tag>
                    </div>
                  </div>
                </div>
                <div class="card stat-card">
                  <div class="card-body">
                    <div class="stat-main">
                      <span class="label">良率波动率</span>
                      <span class="value">1.2%</span>
                      <el-tag type="info">稳定</el-tag>
                    </div>
                  </div>
                </div>
              </div>
              <div class="card chart-card-lg mt-16">
                <div class="card-header"><h4 class="card-title">关键指标汇总与帕累托图柱状分析</h4></div>
                <div class="card-body">
                  <div id="paretoChart" class="chart-container-sm"></div>
                </div>
              </div>
            </div>

            <!-- QC View: Control Charts, Run Chart -->
            <div v-show="activeRole === 'qc'" class="role-view animate-fade-in">
              <div class="card chart-card-lg">
                <div class="card-header"><h4 class="card-title">X-bar 控制图 (SPC 实时监测)</h4></div>
                <div class="card-body">
                  <div id="controlChart" class="chart-container-sm"></div>
                </div>
              </div>
              <div class="card chart-card-lg mt-16">
                <div class="card-header"><h4 class="card-title">Run Chart (全生命周期运行趋势)</h4></div>
                <div class="card-body">
                  <div id="runChart" class="chart-container-sm"></div>
                </div>
              </div>
            </div>

            <!-- Process View: Causal/Fishbone, Network Diagram -->
            <div v-show="activeRole === 'process'" class="role-view animate-fade-in">
               <div class="card chart-card-lg">
                <div class="card-header"><h4 class="card-title">质量根因因果链路 (Fishbone Mapping)</h4></div>
                <div class="card-body">
                  <div id="fishboneChart" class="chart-container-sm"></div>
                </div>
              </div>
              <div class="card chart-card-lg mt-16">
                <div class="card-header"><h4 class="card-title">设备-参数-质量网状拓扑图</h4></div>
                <div class="card-body">
                  <div id="networkChart" class="chart-container-sm"></div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="action-footer mt-24">
           <el-button type="success" size="large" class="btn-glow" @click="reset">沉淀至专家库并返回</el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, nextTick, markRaw, watch } from 'vue'
import { useRouter } from 'vue-router'
import { 
  Upload, Cpu, PieChart, CircleCheck, ArrowLeft, 
  UploadFilled, Check, Download, Loading, View, Odometer, Connection, Management 
} from '@element-plus/icons-vue'
import { ElMessage, ElLoading } from 'element-plus'
import * as echarts from 'echarts'

const router = useRouter()
const currentStep = ref(0)
const loading = ref(false)
const scanProgress = ref(0)
const diagnosticLogs = ref([])

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

const activeConfigCollapse = ref([])
const diagnosisConfig = ref({
  focusMetrics: [],
  analysisGoal: 'root_cause',
  depth: 3,
})

const goToSOP = () => {
  currentStep.value = 6
  nextTick(() => {
    initDashboardCharts()
  })
}

const archiveSop = () => ElMessage.success('SOP 已成功归档至企业专家知识库')
const downloadWord = () => ElMessage.info('Word 报告生成中...')

const initDashboardCharts = () => {
  initParetoChart()
  initControlChart()
  initRunChart()
  initFishboneChart()
  initNetworkChart()
}

const initParetoChart = () => {
  const dom = document.getElementById('paretoChart')
  if (!dom) return
  const chart = echarts.init(dom)
  chart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
    xAxis: { type: 'category', data: ['磨损', '振动', '压力', '温度', '其他'] },
    yAxis: [{ type: 'value', name: '频次' }, { type: 'value', name: '百分比', axisLabel: { formatter: '{value}%' } }],
    series: [
      { name: '频次', type: 'bar', data: [80, 50, 40, 20, 10], itemStyle: { color: '#409eff' } },
      { name: '累计百分比', type: 'line', yAxisIndex: 1, data: [40, 65, 85, 95, 100], itemStyle: { color: '#67c23a' } }
    ]
  })
}

const initControlChart = () => {
  const dom = document.getElementById('controlChart')
  if (!dom) return
  const chart = echarts.init(dom)
  chart.setOption({
    title: { text: 'X-bar 控制图', left: 'center', textStyle: { fontSize: 12 } },
    xAxis: { type: 'category', data: ['T1', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'T8'] },
    yAxis: { type: 'value', min: 14, max: 16 },
    series: [
      {
        data: [14.8, 15.0, 15.2, 14.7, 15.1, 15.4, 14.9, 15.0],
        type: 'line',
        smooth: true,
        markLine: {
          data: [
            { yAxis: 15.5, lineStyle: { color: '#ef4444' } },
            { yAxis: 14.85, lineStyle: { color: '#10b981' } },
            { yAxis: 14.2, lineStyle: { color: '#ef4444' } }
          ]
        }
      }
    ]
  })
}

const initRunChart = () => {
  const dom = document.getElementById('runChart')
  if (!dom) return
  const chart = echarts.init(dom)
  chart.setOption({
    xAxis: { type: 'category', data: ['W1', 'W2', 'W3', 'W4', 'W5', 'W6'] },
    yAxis: { type: 'value', name: '合格率' },
    series: [{ data: [88, 90, 89, 94, 96, 98.4], type: 'line', smooth: true, areaStyle: { opacity: 0.2 } }]
  })
}

const initFishboneChart = () => {
  const dom = document.getElementById('fishboneChart')
  if (!dom) return
  const chart = echarts.init(dom)
  chart.setOption({
    series: [{
      type: 'tree',
      data: [{
        name: '工艺缺陷',
        children: [
          { name: '人', children: [{ name: '培训不足' }] },
          { name: '机', children: [{ name: '振动异常' }] },
          { name: '法', children: [{ name: '进给异常' }] }
        ]
      }],
      symbolSize: 10, label: { position: 'left', fontSize: 11 },
      leaves: { label: { position: 'right' } }
    }]
  })
}

const initNetworkChart = () => {
  const dom = document.getElementById('networkChart')
  if (!dom) return
  const chart = echarts.init(dom)
  chart.setOption({
    series: [{
      type: 'graph',
      layout: 'force',
      data: [{ name: '设备' }, { name: '参数' }, { name: '质量' }, { name: '反馈' }],
      links: [{ source: '设备', target: '参数' }, { source: '参数', target: '质量' }, { source: '质量', target: '反馈' }],
      force: { repulsion: 200 }, label: { show: true }
    }]
  })
}

watch(activeRole, () => {
  nextTick(() => initDashboardCharts())
})

const filter = ref({
  device: '3号精密磨床',
  timeRange: '7d',
  operator: ''
})

const uploadedData = ref([])
const totalRecords = ref(0)
const filePaths = ref([])
const fileList = ref([])
const uploadWarning = ref('')
const diagnosisResult = ref(null)
const solutions = ref([])

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
  const mask = ElLoading.service({ text: '正在进行统计显著性计算...', background: 'rgba(255, 255, 255, 0.8)' })
  setTimeout(() => {
    ttestDataUploaded.value = true
    nextTick(() => initDistributionChart())
    mask.close()
    ElMessage.success('T-test 分析完成：P < 0.05，改善显著')
  }, 1500)
}

const initDistributionChart = () => {
  const chartDom = document.getElementById('distributionChart')
  if (!chartDom) return
  const myChart = echarts.init(chartDom)
  myChart.setOption({
    title: { text: '异常特征分布对比', left: 'center', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'axis' },
    legend: { top: 'bottom', data: ['初始采样 (Before)', '生产验证 (After)'] },
    xAxis: { type: 'category', data: ['0-5μm', '5-10μm', '10-15μm', '15-20μm', '>20μm'] },
    yAxis: { type: 'value', name: '频次' },
    series: [
      {
        name: '初始采样 (Before)',
        type: 'line',
        smooth: true,
        data: [10, 45, 80, 55, 30],
        lineStyle: { color: '#94a3b8', width: 2, type: 'dashed' },
        symbol: 'none'
      },
      {
        name: '生产验证 (After)',
        type: 'line',
        smooth: true,
        data: [5, 15, 35, 20, 8],
        lineStyle: { color: '#409eff', width: 3 },
        areaStyle: { color: 'rgba(64, 158, 255, 0.2)' },
        symbol: 'circle'
      }
    ]
  })
}

const initVerificationCharts = () => {
  const chartDom = document.getElementById('verificationChart')
  if (!chartDom) return
  const myChart = echarts.init(chartDom)
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
}

const handleFileChange = async (uploadFile) => {
  const file = uploadFile.raw
  if (!file) return

  const formData = new FormData()
  formData.append('file', file)

  try {
    const res = await fetch('/api/upload/file', {
      method: 'POST',
      body: formData
    })
    const data = await res.json()
    if (data.code === 200) {
      filePaths.value.push(data.data.file_path)
      uploadedData.value = uploadedData.value.concat(data.data.records)
      totalRecords.value += data.data.total_records
      if (data.warning) {
        uploadWarning.value = data.warning
        ElMessage.warning(data.warning)
      }
      ElMessage.success(`${file.name} 解析成功`)
      // Auto-expand config panel when files are uploaded
      if (!activeConfigCollapse.value.includes('config')) {
        activeConfigCollapse.value = ['config']
      }
    } else if (data.detail) {
      ElMessage.error(data.detail)
    } else {
      ElMessage.error(`${file.name} 上传失败`)
    }
  } catch (e) {
    ElMessage.error(`${file.name} 上传失败，请检查网络连接或后端服务`)
  }
}

const handleFileRemove = () => {
  uploadedData.value = []
  totalRecords.value = 0
  filePaths.value = []
  fileList.value = []
  uploadWarning.value = ''
}

const startAIScan = () => {
  if (uploadedData.value.length === 0) {
    ElMessage.warning('请先上传质量报表')
    return
  }
  currentStep.value = 1
  scanProgress.value = 0
  diagnosticLogs.value = []
  
  const processSteps = [
    '解构原始张量数据...',
    '对齐设备历史维护记录...',
    '启动多层感知机异常推理...',
    '捕获微米级尺寸波动关联项...',
    '诊断链路构建完成。'
  ]
  
  let stepIdx = 0
  const interval = setInterval(() => {
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
      clearInterval(interval)
      fetchDiagnosisResult()
    }
  }, 100)
}

const fetchDiagnosisResult = async () => {
  try {
    const res = await fetch('/api/diagnosis/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        file_paths: filePaths.value,
        equipment: filter.value.device || '3号精密磨床',
        days: filter.value.timeRange === '24h' ? 1 : 7,
        operator: filter.value.operator || null,
        material: null,
        environment: null,
        focus_metrics: diagnosisConfig.value.focusMetrics,
        analysis_goal: diagnosisConfig.value.analysisGoal,
        depth: diagnosisConfig.value.depth,
        time_range: filter.value.timeRange,
      }),
    })
    const data = await res.json()
    if (data.code === 200) {
      diagnosisResult.value = data.data
      currentStep.value = 2
      nextTick(() => initTrendChart())
    }
  } catch (e) {
    ElMessage.error('诊断异常')
    currentStep.value = 0
  }
}

const initTrendChart = () => {
  const chartDom = document.getElementById('trendChart')
  if (!chartDom) return
  const myChart = echarts.init(chartDom)
  const option = {
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { 
      type: 'category', 
      data: diagnosisResult.value.quality_trend.dates,
      axisLine: { lineStyle: { color: '#E4E7ED' } }
    },
    yAxis: { 
      type: 'value', 
      min: 80, 
      max: 100,
      splitLine: { lineStyle: { type: 'dashed' } }
    },
    series: [{
      data: diagnosisResult.value.quality_trend.rates,
      type: 'line',
      smooth: true,
      symbol: 'circle',
      symbolSize: 8,
      itemStyle: { color: '#409eff' },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(64, 158, 255, 0.3)' },
          { offset: 1, color: 'rgba(64, 158, 255, 0)' }
        ])
      }
    }]
  }
  myChart.setOption(option)
}

const initPortraitCharts = () => {
  // Radar Chart
  const radarDom = document.getElementById('radarChart')
  if (radarDom) {
    const radarChart = echarts.init(radarDom)
    radarChart.setOption({
      radar: {
        indicator: [
          { name: '人员 (Man)', max: 100 },
          { name: '机器 (Machine)', max: 100 },
          { name: '材料 (Material)', max: 100 },
          { name: '方法 (Method)', max: 100 },
          { name: '环境 (Env)', max: 100 },
          { name: '测量 (Measure)', max: 100 }
        ],
        splitNumber: 4,
        axisLine: { lineStyle: { color: 'rgba(64,158,255, 0.2)' } },
        splitLine: { lineStyle: { color: 'rgba(64,158,255, 0.2)' } },
        splitArea: { areaStyle: { color: ['rgba(255,255,255,1)', 'rgba(235,245,255,0.3)'] } }
      },
      series: [{
        type: 'radar',
        data: [
          {
            value: [85, 45, 90, 60, 75, 80], // Mock portrait values based on diagnosis
            name: '当前质量态势',
            areaStyle: { color: 'rgba(64, 158, 255, 0.4)' },
            lineStyle: { color: '#409eff', width: 2 },
            itemStyle: { color: '#409eff' }
          }
        ]
      }]
    })
  }

  // Predictor Chart (Bar/Line combination)
  const predictorDom = document.getElementById('predictorChart')
  if (predictorDom) {
    const predictorChart = echarts.init(predictorDom)
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
  }
}

const handleGenerateSolutions = async () => {
  const mask = ElLoading.service({ text: '正在规划最佳改进路径...', background: 'rgba(255, 255, 255, 0.8)' })
  try {
    const res = await fetch('/api/solution/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        root_causes: diagnosisResult.value.root_causes,
        equipment: filter.value.device || null,
      }),
    })
    const data = await res.json()
    solutions.value = data.data.solutions
    currentStep.value = 3
    nextTick(() => initPortraitCharts())
  } finally {
    mask.close()
  }
}

const getTagType = (cat) => {
  if (cat === '设备') return 'danger'
  if (cat === '环境') return 'warning'
  return 'info'
}

const createWorkOrder = (sol) => ElMessage.success(`工单已派发至：${sol.responsible}`)
const exportReport = () => ElMessage.success('方案报告已生成并自动下载')
const previewReport = () => ElMessage.info('正在加载报告预览容器...')

const reset = () => {
  currentStep.value = 0
  uploadedData.value = []
  router.push('/')
}
</script>

<style scoped>
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
  padding: 32px;
  margin-bottom: 32px;
}

.custom-steps {
  max-width: 1000px;
  margin: 0 auto;
}

/* Upload Card Styles */
.upload-card {
  max-width: 1000px;
  margin: 0 auto;
}

.upload-area {
  margin-bottom: 32px;
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

.warning-banner-box {
  margin-bottom: 24px;
}

.filter-panel {
  display: flex;
  gap: 24px;
  padding: 20px;
  background-color: #f8fafc;
  border-radius: 8px;
  margin-bottom: 32px;
}

.filter-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
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
  grid-template-columns: 1fr 1.2fr;
  gap: 24px;
}

.chart-container {
  height: 380px;
}

.chart-container-sm {
  height: 280px;
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

.decision-label {
  font-size: 16px;
  font-weight: 600;
  color: #1e293b;
}

.decision-btns {
  display: flex;
  gap: 16px;
}

/* T-test Styles */
.ttest-card {
  max-width: 1100px;
  margin: 0 auto;
}

.ttest-layout {
  display: flex;
  flex-direction: column;
  gap: 32px;
}

.ttest-upload-section {
  padding: 40px;
  border: 2px dashed #e2e8f0;
  border-radius: 16px;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.upload-title {
  font-size: 18px;
  font-weight: 700;
  color: #334155;
}

/* Dashboard & SOP Mode Styles */
.dashboard-mode {
  width: 100%;
}

.role-selector {
  margin-bottom: 24px;
  padding: 16px 24px;
  display: flex;
  align-items: center;
  gap: 20px;
  background: white;
}

.selector-label {
  font-weight: 700;
  color: #475569;
  font-size: 14px;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: 380px 1fr;
  gap: 24px;
  align-items: start;
}

/* SOP Document Styling */
.sop-document {
  position: sticky;
  top: 20px;
  height: calc(100vh - 300px);
  display: flex;
  flex-direction: column;
}

.scrollable-content {
  overflow-y: auto;
  flex: 1;
}

.sop-content {
  padding: 16px 4px;
}

.sop-section {
  margin-bottom: 24px;
}

.sop-title {
  font-size: 15px;
  font-weight: 800;
  color: #1e293b;
  border-left: 4px solid var(--primary);
  padding-left: 10px;
  margin-bottom: 12px;
}

.sop-section p {
  font-size: 13px;
  color: #475569;
  line-height: 1.6;
}

.sop-mini-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
  margin-top: 8px;
}

.sop-mini-table th, .sop-mini-table td {
  border: 1px solid #e2e8f0;
  padding: 8px;
  text-align: left;
}

.sop-mini-table th {
  background: #f8fafc;
  color: #64748b;
}

/* Report View & Role Specifics */
.report-view {
  min-width: 0;
}

.report-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.stat-main {
  display: flex;
  align-items: center;
  gap: 12px;
}

.stat-main .label {
  font-size: 12px;
  color: #64748b;
  flex: 1;
}

.stat-main .value {
  font-size: 20px;
  font-weight: 800;
  color: #1e293b;
}

.chart-card-lg {
  background: white;
  border-radius: 12px;
  border: 1px solid var(--border-light);
}

/* Metric Cards in T-test */
.metric-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
  margin-top: 16px;
}

.metric-card {
  padding: 16px;
  background: #f8fafc;
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  border: 1px solid #f1f5f9;
}

/* Responsive Dashboard Queries */
@media (max-width: 1024px) {
  .dashboard-grid {
    grid-template-columns: 1fr;
  }
  .sop-document {
    position: static;
    height: auto;
  }
}

@media (max-width: 640px) {
  .report-row {
    grid-template-columns: 1fr;
  }
  .role-selector {
    flex-direction: column;
    align-items: flex-start;
  }
}

.animate-fade-in {
  animation: fadeIn 0.3s ease-out forwards;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}


.mini-upload {
  width: 100%;
  max-width: 400px;
}

.validation-status {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #10b981;
  background: #f0fdf4;
  padding: 8px 16px;
  border-radius: 20px;
}

.ttest-results-section {
  border-top: 1px solid #f1f5f9;
  padding-top: 32px;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
  margin-top: 16px;
}

.metric-card {
  padding: 16px;
  background: #f8fafc;
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  border: 1px solid #f1f5f9;
}

.metric-card .label { font-size: 12px; color: #64748b; font-weight: 600; }
.metric-card .value { font-size: 20px; font-weight: 800; }
.metric-card .hint { font-size: 11px; color: #94a3b8; }
.text-dark { color: #1e293b; }

/* Attribution Analysis Styles */
.attribution-card {
  height: 100%;
}

.attribution-content {
  padding: 8px;
}

.summary-stat {
  display: flex;
  gap: 24px;
  margin-bottom: 32px;
  background: #f8fafc;
  padding: 20px;
  border-radius: 12px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-item .label {
  font-size: 12px;
  color: #64748b;
}

.stat-item .value {
  font-size: 24px;
  font-weight: 800;
}

.text-success { color: #10b981; }
.text-primary { color: #3b82f6; }

.sub-title {
  font-size: 14px;
  font-weight: 700;
  color: #1e293b;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.logic-desc {
  font-size: 13px;
  color: #475569;
  line-height: 1.6;
  margin: 4px 0 0;
}

.animate-fade-in {
  animation: fadeIn 0.3s ease-out forwards;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

/* Config Panel Styles */
.config-collapse {
  margin-bottom: 24px;
  border: 1px solid var(--border-light);
  border-radius: 8px;
  background: #fff;
}

:deep(.config-collapse .el-collapse-item__header) {
  font-weight: 600;
  font-size: 15px;
  padding: 0 20px;
  background: #f8fafc;
}

.config-panel {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.config-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.config-section-title {
  font-size: 13px;
  font-weight: 600;
  color: #606266;
}

.slider-row {
  display: flex;
  align-items: center;
  gap: 16px;
}

.slider-value {
  font-size: 18px;
  font-weight: 700;
  color: var(--primary);
  min-width: 24px;
  text-align: center;
}

/* Charts & Statistics Section Styles */
.mb-16 { margin-bottom: 16px; }

.charts-section {
  background: #fff;
  border-radius: 12px;
  border: 1px solid var(--border-light);
}

.charts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 16px;
}

.chart-image-wrapper {
  display: flex;
  justify-content: center;
  align-items: center;
  background: #f8fafc;
  border-radius: 8px;
  padding: 12px;
  overflow: hidden;
}

.chart-image {
  max-width: 100%;
  max-height: 300px;
  object-fit: contain;
  border-radius: 4px;
}

.statistics-section {
  background: #fff;
  border-radius: 12px;
  border: 1px solid var(--border-light);
}
</style>

