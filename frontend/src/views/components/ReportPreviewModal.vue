<template>
  <div class="report-preview-page">
    <!-- 顶部操作栏 -->
    <div class="page-header">
      <div class="header-left">
        <el-breadcrumb separator="/">
          <el-breadcrumb-item :to="{ path: '/report/generate' }">
            <span style="color: rgba(255, 255, 255, 0.7)">报告生成</span>
          </el-breadcrumb-item>
          <el-breadcrumb-item :to="{ path: '/report/history' }">
            <span style="color: rgba(255, 255, 255, 0.7)">历史记录</span>
          </el-breadcrumb-item>
          <el-breadcrumb-item>
            <span style="color: #ffffff; font-weight: 600;">报告预览</span>
          </el-breadcrumb-item>
        </el-breadcrumb>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading-container">
      <el-icon class="is-loading" :size="48"><Loading /></el-icon>
      <p>加载报告中...</p>
    </div>

    <!-- 报告内容 -->
    <template v-else-if="reportData.id">
      <!-- 报告操作栏（固定在内容区顶部） -->
      <div class="report-actions">
        <div class="report-title">
          <h2>{{ reportData.title || '未命名报告' }}</h2>
          <div class="report-meta">
            <el-tag type="info" v-if="reportData.qcNumber">
              {{ reportData.qcNumber }}
            </el-tag>
            <span class="create-time">
              生成时间：{{ formatDate(reportData.createdAt) }}
            </span>
          </div>
        </div>
        <div class="action-buttons">
          <el-button 
            type="primary" 
            :icon="Download" 
            :loading="downloading"
            :disabled="downloadProgress > 0 && downloadProgress < 100"
            @click="handleDownload"
          >
            {{ downloading ? `下载中 ${downloadProgress}%` : '下载 Word 文档' }}
          </el-button>
          <el-button 
            :icon="Refresh" 
            @click="showRegenerateDialog"
          >
            重新生成
          </el-button>
          <el-button 
            :icon="Close"
            @click="handleClose"
          >
            关闭
          </el-button>
        </div>
      </div>

      <!-- 主内容区（三栏布局） -->
      <div class="main-container">
        <!-- 左侧目录 -->
        <div class="left-sidebar" v-if="reportOutline.length > 0">
          <div class="sidebar-header">
            <h3>报告目录</h3>
          </div>
          <el-tree
            :data="reportOutline"
            :props="{ label: 'label', children: 'children' }"
            highlight-current
            @node-click="handleNodeClick"
          >
            <template #default="{ node }">
              <span class="tree-node">
                <el-icon class="status-icon"><CircleCheck /></el-icon>
                <span>{{ node.label }}</span>
              </span>
            </template>
          </el-tree>
        </div>

        <!-- 中间报告内容 -->
        <div class="content-area" :class="{ 'no-sidebar': reportOutline.length === 0 }">
          <div class="report-content" ref="reportContentRef" @click="handleContentClick">
            <div v-if="reportData.content" v-html="processedContent" class="report-content-body"></div>
            <el-empty v-else description="暂无报告内容" />
          </div>
        </div>

        <!-- 右侧数据源 -->
        <div class="right-sidebar is-visible">
          <div class="sidebar-header">
            <h3>数据来源面板</h3>
            <el-icon class="close-icon" @click="closeDataSource">
              <Close />
            </el-icon>
          </div>
          
          <div class="data-source-tree-container">
            <el-tree
              ref="sourceTreeRef"
              :data="sourceTreeData"
              node-key="id"
              highlight-current
              default-expand-all
              :expand-on-click-node="false"
              @node-click="handleSourceNodeClick"
            >
              <template #default="{ node, data }">
                <span class="custom-tree-node">
                  <el-icon v-if="data.type === 'product'"><Box /></el-icon>
                  <el-icon v-else-if="data.type === 'kit'"><Collection /></el-icon>
                  <el-icon v-else-if="data.type === 'part'"><Setting /></el-icon>
                  <el-icon v-else-if="data.type === 'attachment'"><Document /></el-icon>
                  <span class="node-label">{{ node.label }}</span>
                </span>
              </template>
            </el-tree>
          </div>

          <transition name="fade">
            <div v-if="selectedDataSourceNode" class="data-source-detail">
              <h4>附件详情</h4>
              <div class="detail-item">
                <div class="label">文件名</div>
                <div class="value">{{ selectedDataSourceNode.fileName }}</div>
              </div>
              <div class="detail-item">
                <div class="label">完整路径</div>
                <div class="value">
                  <el-breadcrumb separator="/">
                    <el-breadcrumb-item v-for="seg in selectedDataSourceNode.pathSegments" :key="seg">
                      {{ seg }}
                    </el-breadcrumb-item>
                  </el-breadcrumb>
                </div>
              </div>
              <div class="detail-item">
                <div class="label">数据表名</div>
                <div class="value code-font">{{ selectedDataSourceNode.tableName }}</div>
              </div>
              <div class="detail-item">
                <div class="label">字段名</div>
                <div class="value code-font">{{ selectedDataSourceNode.fieldName }}</div>
              </div>
            </div>
          </transition>
        </div>
      </div>
    </template>

    <!-- 报告不存在 -->
    <div v-else class="error-container">
      <el-empty description="报告不存在或已被删除">
        <el-button type="primary" @click="handleClose">返回</el-button>
      </el-empty>
    </div>

    <!-- 重新生成确认对话框 -->
    <el-dialog v-model="regenerateDialogVisible" title="确认重新生成" width="400px">
      <p style="margin: 0; color: #606266; font-size: 14px;">
        重新生成将覆盖当前报告，是否继续？
      </p>
      <template #footer>
        <el-button @click="regenerateDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="regenerating" @click="handleRegenerate">
          确认
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getReportDetail, downloadReport, regenerateReport, getDataSourceInfo } from '@/api/report'
import { CircleCheck, Close, Download, Refresh, Loading, Box, Collection, Setting, Document } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const emit = defineEmits(['close'])
const props = defineProps({
  id: {
    type: String,
    default: ''
  }
})

const route = useRoute()
const router = useRouter()
const reportId = props.id || route?.params?.id || 'IP-001'

// ✅ 处理报告内容
const processedContent = computed(() => {
  if (!reportData.value.content) return ''
  
  let content = reportData.value.content
  
  // 0. 清理表格：移除空数据列
  try {
    const parser = new DOMParser()
    const doc = parser.parseFromString(content, 'text/html')
    const tables = doc.querySelectorAll('table')
    
    tables.forEach(table => {
      // 排除封面签名表 (包含编制单位等特征文字)
      if (table.textContent.includes('编制单位') || table.textContent.includes('审核') || table.textContent.includes('批准')) {
        return
      }

      const rows = Array.from(table.querySelectorAll('tr'))
      if (rows.length <= 1) return 

      // 1. 获取最大列数和空列索引
      let maxCols = 0
      rows.forEach(row => {
        maxCols = Math.max(maxCols, row.cells.length)
      })

      const emptyColIndices = []
      for (let j = 0; j < maxCols; j++) {
        let allEmpty = true
        for (let i = 0; i < rows.length; i++) {
          const cell = rows[i].cells[j]
          if (cell && cell.textContent.replace(/\u00a0/g, ' ').trim().length > 0) {
            allEmpty = false
            break
          }
        }
        if (allEmpty) {
          emptyColIndices.push(j)
        }
      }

      // 2. 从后往前删除空列
      for (let k = emptyColIndices.length - 1; k >= 0; k--) {
        const colIndex = emptyColIndices[k]
        rows.forEach(row => {
          if (row.cells[colIndex]) {
            row.deleteCell(colIndex)
          }
        })
      }

      // 3. 🛑 识别性能表并添加表头和标题
      // 检查第一行第一列是否为 "1"，第二列是否为产品编号 (4-6位数字)
      const firstDataRow = rows[0]
      const firstCellText = firstDataRow.cells[0]?.textContent?.trim()
      const secondCellText = firstDataRow.cells[1]?.textContent?.trim()
      
      if (firstCellText === '1' && /^\d{4,6}$/.test(secondCellText)) {
        // 创建表头行
        const headerRow = document.createElement('tr')
        // 根据当前列数创建表头，通常为 7 列
        const colCount = firstDataRow.cells.length
        const headers = ['序号', '产品编号', '密封性', '绝缘电阻', '开启时间', '关闭时间', '额定流量', '重量']
        
        for (let i = 0; i < colCount; i++) {
          const th = document.createElement('th')
          th.textContent = headers[i] || `参数${i - 1}`
          th.style.backgroundColor = '#FAFAFA'
          th.style.fontWeight = '600'
          th.style.border = '1px solid #E8E8E8'
          th.style.padding = '8px 12px'
          headerRow.appendChild(th)
        }
        
        // 插入到表格最前面
        table.insertBefore(headerRow, table.firstChild)
        
        // 在表格前添加标题
        const titleDiv = document.createElement('div')
        titleDiv.innerHTML = '<p style="font-weight: bold; font-size: 16px; margin-top: 24px; margin-bottom: 12px; text-align: left; color: #262626;">附表12.19 增压电磁阀性能表</p>'
        table.parentNode.insertBefore(titleDiv, table)
      }
    })
    content = doc.body.innerHTML
  } catch (e) {
    console.error('Table cleanup failed:', e)
  }

  // 1. 处理 4-12 位数字的产品编号 (如 25024, 8424)
  // 排除已经在 span 标签内的，以及 HTML 属性中的
  content = content.replace(/(?<!class="dynamic-data"[^>]*>)\b(\d{4,12})\b(?![^<]*>)/g, '<span class="product-number-blue">$1</span>')
  
  // 2. 处理 XX-0 这种型号
  content = content.replace(/(?<!class="dynamic-data"[^>]*>)\b(XX-0)\b(?![^<]*>)/g, '<span class="product-number-blue">$1</span>')
  
  // 3. 处理表格中的数值 (所有表格单元格内的数值标记为蓝色)
  content = content.replace(/(<td[^>]*>)([\s\S]*?)(<\/td>)/g, (match, openingTag, cellContent, closingTag) => {
    // 排除已经在标签内的数字，以及 HTML 属性中的数字
    const highlighted = cellContent.replace(/(?<!<[^>]*)\b(\d+\.?\d*)\b(?![^<]*>)/g, '<span class="product-number-blue">$1</span>')
    return openingTag + highlighted + closingTag
  })

  // 4. 修复封面签名栏布局 (按照行合并左侧空白格)
  // 移除那个带 rowspan=9 的空白单元格
  content = content.replace(/<td[^>]*rowspan=9[^>]*>[\s\S]*?<\/td>/g, '')
  // 将签名栏标签单元格的 colspan 从 4 增加到 5，以合并左侧移除的空间
  const signatureLabels = ['编制单位', '编写', '校对', '审核', '复核', '批准']
  signatureLabels.forEach(label => {
    const reg = new RegExp(`(<td[^>]*${label}[^>]*colspan=)("?)4("?)`, 'g')
    content = content.replace(reg, '$1$2 5 $3')
  })

  return content
})

// 报告数据
const reportData = ref({
  id: 'QC-2026-0513',
  title: '增压电磁阀产品生产质量报告',
  qcNumber: '13JPSBG-2025194',
  createdAt: '2026/05/14 06:58',
 content: `
      <div style="
        max-width: 900px;
        margin: 0 auto;
        padding: 20px;
        font-family: 'Microsoft YaHei', '微软雅黑', Arial, sans-serif;
        font-size: 14px;
        line-height: 1.8;
        color: #333;
      ">

<!--StartFragment--><div class="Section0"  style="layout-grid:15.6000pt;" ><table class=MsoNormalTable  border=1  cellspacing=0  style="border-collapse:collapse;margin-left:-90.1000pt;mso-table-layout-alt:fixed;
border:none;mso-border-left-alt:0.5000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;
mso-border-right-alt:0.5000pt solid windowtext;mso-border-bottom-alt:0.5000pt solid windowtext;mso-border-insideh:0.5000pt solid windowtext;
mso-border-insidev:0.5000pt solid windowtext;mso-padding-alt:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;" ><tr style="height:18.8500pt;page-break-inside:avoid;" ><td width=213  valign=bottom  rowspan=10  style="width:106.8500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:none;
mso-border-left-alt:none;border-right:none;mso-border-right-alt:none;
border-top:none;mso-border-top-alt:none;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="margin-left:0.6000pt;text-indent:-0.6000pt;text-align:center;" ><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';letter-spacing:1.0000pt;mso-ansi-font-weight:bold;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >会签</font></span></b><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';letter-spacing:1.0000pt;mso-ansi-font-weight:bold;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></b></p></td><td width=888  valign=top  colspan=11  style="width:444.2000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:4.5000pt solid rgb(255,0,0);
mso-border-left-alt:4.5000pt solid rgb(255,0,0);border-right:4.5000pt solid rgb(255,0,0);mso-border-right-alt:4.5000pt solid rgb(255,0,0);
border-top:4.5000pt solid rgb(255,0,0);mso-border-top-alt:4.5000pt solid rgb(255,0,0);border-bottom:none;
mso-border-bottom-alt:none;" ><p class=MsoNormal  style="margin-left:0.8000pt;text-indent:-0.8000pt;line-height:18.0000pt;
mso-line-height-rule:exactly;" ><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';letter-spacing:1.0000pt;mso-ansi-font-weight:bold;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></b></p></td></tr><tr style="height:18.2500pt;page-break-inside:avoid;" ><td width=147  valign=top  colspan=2  style="width:73.8500pt;padding:0.0000pt 2.8500pt 0.0000pt 2.8500pt ;border-left:4.5000pt solid rgb(255,0,0);
mso-border-left-alt:4.5000pt solid rgb(255,0,0);border-right:none;mso-border-right-alt:none;
border-top:none;mso-border-top-alt:none;border-bottom:none;
mso-border-bottom-alt:none;" ><p class=MsoNormal  align=right  style="margin-right:10.5000pt;margin-left:0.6000pt;text-indent:-0.6000pt;
mso-char-indent-count:-0.0500;text-align:right;line-height:20.0000pt;
mso-line-height-rule:exactly;" ><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';mso-ansi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" ><font face="SimSun" >档号</font></span></b><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';mso-ansi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" ><o:p></o:p></span></b></p></td><td width=186  valign=top  colspan=2  style="width:93.4000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:none;
mso-border-left-alt:none;border-right:none;mso-border-right-alt:none;
border-top:none;mso-border-top-alt:none;border-bottom:none;
mso-border-bottom-alt:none;" ><p class=MsoNormal  style="margin-left:0.7000pt;text-indent:-0.7000pt;line-height:20.0000pt;
mso-line-height-rule:exactly;" ><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';letter-spacing:1.0000pt;mso-ansi-font-weight:bold;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></b></p></td><td width=141  valign=top  colspan=2  style="width:70.8500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:none;
mso-border-left-alt:none;border-right:none;mso-border-right-alt:none;
border-top:none;mso-border-top-alt:none;border-bottom:none;
mso-border-bottom-alt:none;" ><p class=MsoNormal  style="margin-left:0.7000pt;text-indent:-0.7000pt;line-height:20.0000pt;
mso-line-height-rule:exactly;" ><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';letter-spacing:1.0000pt;mso-ansi-font-weight:bold;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></b></p></td><td width=135  valign=top  style="width:67.8000pt;padding:0.0000pt 1.4000pt 0.0000pt 1.4000pt ;border-left:none;
mso-border-left-alt:none;border-right:none;mso-border-right-alt:none;
border-top:none;mso-border-top-alt:none;border-bottom:none;
mso-border-bottom-alt:none;" ><p class=MsoNormal  align=center  style="margin-left:0.6000pt;text-indent:-0.6000pt;text-align:center;" ><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';mso-ansi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:0.0000pt;" ><font face="SimSun" >编号</font></span></b><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';mso-ansi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:0.0000pt;" ><o:p></o:p></span></b></p></td><td width=236  valign=top  colspan=3  style="width:118.3000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:none;
mso-border-left-alt:none;border-right:none;mso-border-right-alt:none;
border-top:none;mso-border-top-alt:none;border-bottom:1.0000pt solid rgb(255,0,0);
mso-border-bottom-alt:0.7500pt solid rgb(255,0,0);" ><p class=MsoNormal  style="margin-left:0.4500pt;text-indent:-0.4500pt;line-height:20.0000pt;
mso-line-height-rule:exactly;" ><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';mso-ansi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" >13JPSBG-2025</span></b><b style="mso-bidi-font-weight:normal" ><span style="font-family:SimSun;mso-ansi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >194</font></span></b><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';mso-ansi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" ><o:p></o:p></span></b></p></td><td width=40  valign=top  rowspan=3  style="width:20.0000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:none;
mso-border-left-alt:none;border-right:4.5000pt solid rgb(255,0,0);mso-border-right-alt:4.5000pt solid rgb(255,0,0);
border-top:none;mso-border-top-alt:none;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  style="line-height:20.0000pt;mso-line-height-rule:exactly;" ><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';letter-spacing:1.0000pt;mso-ansi-font-weight:bold;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></b></p><p class=MsoNormal  style="margin-left:0.8000pt;text-indent:-0.8000pt;line-height:20.0000pt;
mso-line-height-rule:exactly;" ><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';letter-spacing:1.0000pt;mso-ansi-font-weight:bold;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></b></p><p class=MsoNormal  style="margin-left:0.8000pt;text-indent:-0.8000pt;line-height:20.0000pt;
mso-line-height-rule:exactly;" ><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';letter-spacing:1.0000pt;mso-ansi-font-weight:bold;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></b></p></td></tr><tr style="height:18.8500pt;page-break-inside:avoid;" ><td width=147  valign=top  colspan=2  style="width:73.8500pt;padding:0.0000pt 2.8500pt 0.0000pt 2.8500pt ;border-left:4.5000pt solid rgb(255,0,0);
mso-border-left-alt:4.5000pt solid rgb(255,0,0);border-right:none;mso-border-right-alt:none;
border-top:none;mso-border-top-alt:none;border-bottom:none;
mso-border-bottom-alt:none;" ><p class=MsoNormal  align=right  style="margin-right:10.5000pt;margin-left:-5.3000pt;mso-para-margin-left:-0.5600gd;
text-indent:-0.6000pt;text-align:right;line-height:20.0000pt;
mso-line-height-rule:exactly;" ><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';mso-ansi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:0.0000pt;" ><font face="SimSun" >保管期限</font></span></b><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';mso-ansi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" ><o:p></o:p></span></b></p></td><td width=186  valign=top  colspan=2  style="width:93.4000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:none;
mso-border-left-alt:none;border-right:none;mso-border-right-alt:none;
border-top:none;mso-border-top-alt:none;border-bottom:none;
mso-border-bottom-alt:none;" ><p class=MsoNormal  style="margin-left:0.7000pt;text-indent:-0.7000pt;line-height:20.0000pt;
mso-line-height-rule:exactly;" ><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';letter-spacing:1.0000pt;mso-ansi-font-weight:bold;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></b></p></td><td width=141  valign=top  colspan=2  style="width:70.8500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:none;
mso-border-left-alt:none;border-right:none;mso-border-right-alt:none;
border-top:none;mso-border-top-alt:none;border-bottom:none;
mso-border-bottom-alt:none;" ><p class=MsoNormal  style="margin-left:0.7000pt;text-indent:-0.7000pt;line-height:20.0000pt;
mso-line-height-rule:exactly;" ><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';letter-spacing:1.0000pt;mso-ansi-font-weight:bold;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></b></p></td><td width=135  valign=top  style="width:67.8000pt;padding:0.0000pt 1.4000pt 0.0000pt 1.4000pt ;border-left:none;
mso-border-left-alt:none;border-right:none;mso-border-right-alt:none;
border-top:none;mso-border-top-alt:none;border-bottom:none;" ><p class=MsoNormal  align=center  style="margin-left:0.6000pt;text-indent:-0.6000pt;text-align:center;" ><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';mso-ansi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:0.0000pt;" ><font face="SimSun" >密级</font></span></b><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';mso-ansi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:0.0000pt;" ><o:p></o:p></span></b></p></td><td width=236  valign=top  colspan=3  style="width:118.3000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:none;
mso-border-left-alt:none;border-right:none;mso-border-right-alt:none;
border-top:none;mso-border-top-alt:0.7500pt solid rgb(255,0,0);border-bottom:1.0000pt solid rgb(255,0,0);
mso-border-bottom-alt:0.7500pt solid rgb(255,0,0);" ><p class=MsoNormal  align=center  style="text-align:center;line-height:20.0000pt;mso-line-height-rule:exactly;" ><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';letter-spacing:1.0000pt;mso-ansi-font-weight:bold;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >内部</font></span></b><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';letter-spacing:1.0000pt;mso-ansi-font-weight:bold;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></b></p><p class=MsoNormal  style="margin-left:0.7000pt;text-indent:-0.7000pt;line-height:20.0000pt;
mso-line-height-rule:exactly;" ><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';letter-spacing:1.0000pt;mso-ansi-font-weight:bold;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></b></p><p class=MsoNormal  style="margin-left:0.7000pt;text-indent:-0.7000pt;line-height:20.0000pt;
mso-line-height-rule:exactly;" ><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';letter-spacing:1.0000pt;mso-ansi-font-weight:bold;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></b></p></td></tr><tr style="height:18.8500pt;page-break-inside:avoid;" ><td width=476  valign=top  colspan=6  style="width:238.1000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:4.5000pt solid rgb(255,0,0);
mso-border-left-alt:4.5000pt solid rgb(255,0,0);border-right:none;mso-border-right-alt:none;
border-top:none;mso-border-top-alt:none;border-bottom:none;
mso-border-bottom-alt:none;" ><p class=MsoNormal  style="text-indent:14.0500pt;mso-char-indent-count:1.0000;line-height:20.0000pt;
mso-line-height-rule:exactly;" ><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';letter-spacing:1.0000pt;mso-ansi-font-weight:bold;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></b></p></td><td width=135  valign=top  style="width:67.8000pt;padding:0.0000pt 1.4000pt 0.0000pt 1.4000pt ;border-left:none;
mso-border-left-alt:none;border-right:none;mso-border-right-alt:none;
border-top:none;mso-border-top-alt:none;border-bottom:none;
mso-border-bottom-alt:none;" ><p class=MsoNormal  align=center  style="margin-left:0.2000pt;mso-para-margin-left:-0.1100gd;text-indent:-1.3500pt;
mso-char-indent-count:-0.1100;text-align:center;" ><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';mso-ansi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:0.0000pt;" ><font face="SimSun" >保密期限</font></span></b><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';mso-ansi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:0.0000pt;" ><o:p></o:p></span></b></p></td><td width=236  valign=top  colspan=3  style="width:118.3000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:none;
mso-border-left-alt:none;border-right:none;mso-border-right-alt:none;
border-top:1.0000pt solid rgb(255,0,0);mso-border-top-alt:0.7500pt solid rgb(255,0,0);border-bottom:1.0000pt solid rgb(255,0,0);
mso-border-bottom-alt:0.7500pt solid rgb(255,0,0);" ><p class=MsoNormal  style="margin-left:0.7000pt;text-indent:-0.7000pt;line-height:20.0000pt;
mso-line-height-rule:exactly;" ><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';letter-spacing:1.0000pt;mso-ansi-font-weight:bold;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></b></p></td></tr><tr style="height:44.5000pt;" ><td width=888  valign=top  colspan=11  style="width:444.2000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:none;
mso-border-left-alt:none;border-right:4.5000pt solid rgb(255,0,0);mso-border-right-alt:4.5000pt solid rgb(255,0,0);
border-top:none;mso-border-top-alt:none;border-bottom:none;
mso-border-bottom-alt:none;" ><p class=MsoNormal  style="tab-stops:left blank 329.7500pt ;line-height:20.0000pt;mso-line-height-rule:exactly;" ><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';mso-ansi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:0.0000pt;" ><span style="mso-spacerun:'yes';" >&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span><font face="SimSun" >阶段标记</font> <span style="mso-spacerun:'yes';" >&nbsp;</span></span></b><b style="mso-bidi-font-weight:normal" ><u><span style="font-family:'Times New Roman';mso-ansi-font-weight:bold;text-decoration:underline;
text-underline:rgb(255,0,0) single;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" ><span style="mso-spacerun:'yes';" >&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span>S <span style="mso-spacerun:'yes';" >&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span></span></u></b><b style="mso-bidi-font-weight:normal" ><u><span style="font-family:'Times New Roman';mso-ansi-font-weight:bold;text-decoration:underline;
text-underline:single;font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></u></b></p><p class=MsoNormal  style="line-height:20.0000pt;mso-line-height-rule:exactly;" ><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';mso-ansi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></b></p></td></tr><tr style="height:28.8000pt;page-break-inside:avoid;" ><td width=162  valign=top  colspan=3  style="width:81.2000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:4.5000pt solid rgb(255,0,0);
mso-border-left-alt:4.5000pt solid rgb(255,0,0);border-right:none;mso-border-right-alt:none;
border-top:none;mso-border-top-alt:none;border-bottom:none;
mso-border-bottom-alt:none;" ><p class=MsoNormal  style="line-height:32.0000pt;mso-line-height-rule:exactly;" ><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';mso-ansi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></b></p></td><td width=579  valign=top  colspan=5  rowspan=3  style="width:289.6000pt;padding:8.5000pt 2.8500pt 0.0000pt 2.8500pt ;border-left:none;
mso-border-left-alt:none;border-right:none;mso-border-right-alt:none;
border-top:none;mso-border-top-alt:none;border-bottom:none;
mso-border-bottom-alt:none;" ><p class=MsoDate  align=center  style="text-align:center;" ><u><span style="font-family:SimSun;mso-ascii-font-family:'Times New Roman';mso-hansi-font-family:'Times New Roman';
text-decoration:underline;text-underline:single;font-size:18.0000pt;
mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >XX</font></span></u><u><span style="font-family:'Times New Roman';text-decoration:underline;text-underline:single;
font-size:18.0000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >系列型号</font> </span></u><u><span style="font-family:'Times New Roman';text-decoration:underline;text-underline:single;
font-size:18.0000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></u></p><p class=MsoNormal  align=center  style="margin-left:-4.4000pt;mso-para-margin-left:-0.4200gd;tab-stops:left blank 41.2500pt ;
text-align:center;line-height:110%;" ><u><span style="font-family:SimSun;text-decoration:underline;text-underline:single;
font-size:18.0000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >XX</font></span></u><u><span style="font-family:'Times New Roman';text-decoration:underline;text-underline:single;
font-size:18.0000pt;mso-font-kerning:1.0000pt;" >-0<font face="SimSun" >增压电磁阀</font></span></u><u><span style="font-family:'Times New Roman';text-decoration:underline;text-underline:single;
font-size:18.0000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></u></p><p class=MsoNormal  align=center  style="margin-left:-4.4000pt;mso-para-margin-left:-0.4200gd;tab-stops:left blank 41.2500pt ;
text-align:center;line-height:110%;" ><u><span style="font-family:'Times New Roman';text-decoration:underline;text-underline:single;
font-size:26.0000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >产品生产质量报告</font></span></u><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';mso-ansi-font-weight:bold;font-size:18.0000pt;
mso-font-kerning:1.0000pt;" ><o:p></o:p></span></b></p></td><td width=146  valign=top  colspan=3  style="width:73.4000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:none;
mso-border-left-alt:none;border-right:4.5000pt solid rgb(255,0,0);mso-border-right-alt:4.5000pt solid rgb(255,0,0);
border-top:none;mso-border-top-alt:none;border-bottom:none;
mso-border-bottom-alt:none;" ><p class=MsoNormal  style="margin-left:0.6000pt;text-indent:-0.6000pt;line-height:32.0000pt;
mso-line-height-rule:exactly;" ><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';mso-ansi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></b></p></td></tr><tr style="height:28.8000pt;page-break-inside:avoid;" ><td width=162  valign=top  colspan=3  style="width:81.2000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:4.5000pt solid rgb(255,0,0);
mso-border-left-alt:4.5000pt solid rgb(255,0,0);border-right:none;mso-border-right-alt:none;
border-top:none;mso-border-top-alt:none;border-bottom:none;
mso-border-bottom-alt:none;" ><p class=MsoNormal  style="line-height:32.0000pt;mso-line-height-rule:exactly;" ><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';mso-ansi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></b></p></td><td width=146  valign=top  colspan=3  style="width:73.4000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:none;
mso-border-left-alt:none;border-right:4.5000pt solid rgb(255,0,0);mso-border-right-alt:4.5000pt solid rgb(255,0,0);
border-top:none;mso-border-top-alt:none;border-bottom:none;
mso-border-bottom-alt:none;" ><p class=MsoNormal  style="margin-left:0.6000pt;text-indent:-0.6000pt;line-height:32.0000pt;
mso-line-height-rule:exactly;" ><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';mso-ansi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></b></p></td></tr><tr style="height:31.4500pt;" ><td width=162  valign=top  colspan=3  style="width:81.2000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:4.5000pt solid rgb(255,0,0);
mso-border-left-alt:4.5000pt solid rgb(255,0,0);border-right:none;mso-border-right-alt:none;
border-top:none;mso-border-top-alt:none;border-bottom:none;
mso-border-bottom-alt:none;" ><p class=279  align=center  style="text-indent:0.0000pt;text-align:center;" ><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';letter-spacing:-0.2000pt;mso-ansi-font-weight:bold;
font-size:12.0000pt;mso-font-kerning:10.5000pt;" ><o:p>&nbsp;</o:p></span></b></p></td><td width=146  valign=top  colspan=3  style="width:73.4000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:none;
mso-border-left-alt:none;border-right:4.5000pt solid rgb(255,0,0);mso-border-right-alt:4.5000pt solid rgb(255,0,0);
border-top:none;mso-border-top-alt:none;border-bottom:none;
mso-border-bottom-alt:none;" ><p class=MsoNormal  style="line-height:32.0000pt;mso-line-height-rule:exactly;" ><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';mso-ansi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></b></p></td></tr><tr style="height:54.0500pt;" ><td width=888  valign=top  colspan=11  style="width:444.2000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:none;
mso-border-left-alt:none;border-right:4.5000pt solid rgb(255,0,0);mso-border-right-alt:4.5000pt solid rgb(255,0,0);
border-top:none;mso-border-top-alt:none;border-bottom:none;
mso-border-bottom-alt:none;" ><p class=279  align=center  style="text-indent:0.0000pt;text-align:center;" ><span style="font-family:'Times New Roman';letter-spacing:-0.2000pt;font-size:10.5000pt;
mso-font-kerning:10.5000pt;" ><o:p>&nbsp;</o:p></span></p></td></tr><tr style="height:54.0500pt;" ><td width=888  valign=top  colspan=11  rowspan=3  style="width:444.2000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:none;
mso-border-left-alt:none;border-right:4.5000pt solid rgb(255,0,0);mso-border-right-alt:4.5000pt solid rgb(255,0,0);
border-top:none;mso-border-top-alt:none;border-bottom:none;
mso-border-bottom-alt:none;" ><p class=279  align=center  style="text-indent:0.0000pt;text-align:center;" ><span style="font-family:'Times New Roman';letter-spacing:-0.2000pt;font-size:10.5000pt;
mso-font-kerning:10.5000pt;" ><o:p>&nbsp;</o:p></span></p><p class=279  align=center  style="text-indent:0.0000pt;text-align:center;" ><span style="font-family:'Times New Roman';letter-spacing:-0.2000pt;font-size:10.5000pt;
mso-font-kerning:10.5000pt;" ><o:p>&nbsp;</o:p></span></p></td></tr><tr style="height:13.3000pt;" ><td width=213  valign=top  style="width:106.8500pt;padding:0.0000pt 0.0000pt 0.0000pt 22.7000pt ;border-left:none;
mso-border-left-alt:none;border-right:4.5000pt solid rgb(255,0,0);mso-border-right-alt:4.5000pt solid rgb(255,0,0);
border-top:1.5000pt solid rgb(255,0,0);mso-border-top-alt:1.5000pt solid rgb(255,0,0);border-bottom:1.0000pt solid rgb(255,0,0);
mso-border-bottom-alt:1.0000pt solid rgb(255,0,0);" ><p class=MsoNormal  align=center  style="margin-left:0.4500pt;text-indent:-0.4500pt;text-align:center;" ><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';mso-ansi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></b></p></td></tr><tr style="height:14.8500pt;" ><td width=213  valign=top  style="width:106.8500pt;padding:0.0000pt 0.0000pt 0.0000pt 22.7000pt ;border-left:none;
mso-border-left-alt:none;border-right:4.5000pt solid rgb(255,0,0);mso-border-right-alt:4.5000pt solid rgb(255,0,0);
border-top:none;mso-border-top-alt:1.0000pt solid rgb(255,0,0);border-bottom:1.5000pt solid rgb(255,0,0);
mso-border-bottom-alt:1.5000pt solid rgb(255,0,0);" ><p class=MsoNormal  align=center  style="margin-left:0.4500pt;text-indent:-0.4500pt;text-align:center;" ><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';mso-ansi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></b></p></td></tr><tr style="height:13.3000pt;" ><td width=213  valign=top  style="width:106.8500pt;padding:0.0000pt 0.0000pt 0.0000pt 22.7000pt ;border-left:none;
mso-border-left-alt:none;border-right:none;mso-border-right-alt:none;
border-top:none;mso-border-top-alt:1.5000pt solid rgb(255,0,0);border-bottom:1.0000pt solid rgb(255,0,0);
mso-border-bottom-alt:1.0000pt solid rgb(255,0,0);" ><p class=MsoNormal  align=center  style="margin-left:0.4500pt;text-indent:-0.4500pt;text-align:center;" ><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';mso-ansi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></b></p></td><td width=97  valign=top  rowspan=9  style="width:48.8000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:4.5000pt solid rgb(255,0,0);
mso-border-left-alt:4.5000pt solid rgb(255,0,0);border-right:none;mso-border-right-alt:none;
border-top:none;mso-border-top-alt:none;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  style="line-height:28.0000pt;mso-line-height-rule:exactly;" ><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';mso-ansi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></b></p></td><td width=261  valign=center  colspan=4  rowspan=2  style="width:130.7000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:none;
mso-border-left-alt:none;border-right:none;mso-border-right-alt:none;
border-top:none;mso-border-top-alt:none;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="text-align:center;line-height:26.0000pt;mso-line-height-rule:exactly;" ><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';mso-ansi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;position:relative;top:3.0000pt;
mso-text-raise:-3.0000pt;" ><font face="SimSun" >编制单位</font></span></b><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';mso-ansi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;position:relative;top:3.0000pt;
mso-text-raise:-3.0000pt;" ><o:p></o:p></span></b></p></td><td width=457  valign=bottom  colspan=4  rowspan=2  style="width:228.6500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:none;
mso-border-left-alt:none;border-right:none;mso-border-right-alt:none;
border-top:none;mso-border-top-alt:none;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="text-align:center;line-height:26.0000pt;mso-line-height-rule:exactly;" ><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';mso-ansi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" >13<font face="SimSun" >车间</font></span></b><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';mso-ansi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" ><o:p></o:p></span></b></p></td><td width=72  valign=top  colspan=2  rowspan=9  style="width:36.0500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:none;
mso-border-left-alt:none;border-right:4.5000pt solid rgb(255,0,0);mso-border-right-alt:4.5000pt solid rgb(255,0,0);
border-top:none;mso-border-top-alt:none;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  style="line-height:28.0000pt;mso-line-height-rule:exactly;" ><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';mso-ansi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></b></p></td></tr><tr style="height:13.3000pt;" ><td width=213  valign=top  style="width:106.8500pt;padding:0.0000pt 0.0000pt 0.0000pt 22.7000pt ;border-left:none;
mso-border-left-alt:none;border-right:none;mso-border-right-alt:none;
border-top:none;mso-border-top-alt:1.0000pt solid rgb(255,0,0);border-bottom:1.5000pt solid rgb(255,0,0);
mso-border-bottom-alt:1.5000pt solid rgb(255,0,0);" ><p class=MsoNormal  align=center  style="margin-left:0.4500pt;text-indent:-0.4500pt;text-align:center;" ><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';mso-ansi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></b></p></td></tr><tr style="height:13.3000pt;" ><td width=213  valign=top  nowrap  style="width:106.8500pt;padding:0.0000pt 0.0000pt 0.0000pt 22.7000pt ;border-left:none;
mso-border-left-alt:none;border-right:4.5000pt solid rgb(255,0,0);mso-border-right-alt:4.5000pt solid rgb(255,0,0);
border-top:none;mso-border-top-alt:1.5000pt solid rgb(255,0,0);border-bottom:1.0000pt solid rgb(255,0,0);
mso-border-bottom-alt:1.0000pt solid rgb(255,0,0);" ><p class=MsoNormal  align=center  style="margin-left:0.4500pt;text-indent:-0.4500pt;text-align:center;" ><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';mso-ansi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></b></p></td><td width=261  valign=bottom  colspan=4  rowspan=2  style="width:130.7000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:none;
mso-border-left-alt:none;border-right:none;mso-border-right-alt:none;
border-top:none;mso-border-top-alt:none;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="margin-left:0.7500pt;text-indent:-0.7500pt;text-align:center;
line-height:26.0000pt;mso-line-height-rule:exactly;" ><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';mso-ansi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;position:relative;top:3.0000pt;
mso-text-raise:-3.0000pt;" ><font face="SimSun" >编写（定密承办人）</font></span></b><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';mso-ansi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;position:relative;top:3.0000pt;
mso-text-raise:-3.0000pt;" ><o:p></o:p></span></b></p></td><td width=457  valign=bottom  colspan=4  rowspan=2  style="width:228.6500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:none;
mso-border-left-alt:none;border-right:none;mso-border-right-alt:none;
border-top:none;mso-border-top-alt:none;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="text-align:center;line-height:26.0000pt;mso-line-height-rule:exactly;" ><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';mso-ansi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" ><font face="SimSun" >智静娟</font>20250</span></b><b style="mso-bidi-font-weight:normal" ><span style="font-family:SimSun;mso-ansi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >9</font></span></b><b style="mso-bidi-font-weight:normal" ><span style="font-family:SimSun;mso-ansi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >1</font></span></b><b style="mso-bidi-font-weight:normal" ><span style="font-family:SimSun;mso-ansi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >8</font></span></b><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;mso-ansi-font-weight:bold;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></b></p></td></tr><tr style="height:13.3000pt;" ><td width=213  valign=top  nowrap  style="width:106.8500pt;padding:0.0000pt 0.0000pt 0.0000pt 22.7000pt ;border-left:none;
mso-border-left-alt:none;border-right:4.5000pt solid rgb(255,0,0);mso-border-right-alt:4.5000pt solid rgb(255,0,0);
border-top:none;mso-border-top-alt:1.0000pt solid rgb(255,0,0);border-bottom:1.5000pt solid rgb(255,0,0);
mso-border-bottom-alt:1.5000pt solid rgb(255,0,0);" ><p class=MsoNormal  align=center  style="margin-left:0.4500pt;text-indent:-0.4500pt;text-align:center;" ><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';mso-ansi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></b></p></td></tr><tr style="height:13.3000pt;" ><td width=213  valign=bottom  nowrap  style="width:106.8500pt;padding:0.0000pt 0.0000pt 0.0000pt 22.7000pt ;border-left:none;
mso-border-left-alt:none;border-right:none;mso-border-right-alt:none;
border-top:none;mso-border-top-alt:1.5000pt solid rgb(255,0,0);border-bottom:1.0000pt solid rgb(255,0,0);
mso-border-bottom-alt:1.0000pt solid rgb(255,0,0);" ><p class=MsoNormal  align=center  style="margin-left:0.4500pt;text-indent:-0.4500pt;text-align:center;" ><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';mso-ansi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></b></p></td><td width=261  valign=bottom  colspan=4  rowspan=2  style="width:130.7000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:none;
mso-border-left-alt:none;border-right:none;mso-border-right-alt:none;
border-top:none;mso-border-top-alt:none;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="margin-left:0.7500pt;text-indent:-0.7500pt;text-align:center;
line-height:26.0000pt;mso-line-height-rule:exactly;" ><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';mso-ansi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;position:relative;top:3.0000pt;
mso-text-raise:-3.0000pt;" ><font face="SimSun" >校对</font></span></b><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';mso-ansi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;position:relative;top:3.0000pt;
mso-text-raise:-3.0000pt;" ><o:p></o:p></span></b></p></td><td width=457  valign=bottom  colspan=4  rowspan=2  style="width:228.6500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:none;
mso-border-left-alt:none;border-right:none;mso-border-right-alt:none;
border-top:none;mso-border-top-alt:none;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="text-align:center;line-height:26.0000pt;mso-line-height-rule:exactly;" ><b style="mso-bidi-font-weight:normal" ><span style="font-family:SimSun;mso-ansi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" ><font face="SimSun" >白亚群</font></span></b><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';mso-ansi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" >20250</span></b><b style="mso-bidi-font-weight:normal" ><span style="font-family:SimSun;mso-ansi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >9</font></span></b><b style="mso-bidi-font-weight:normal" ><span style="font-family:SimSun;mso-ansi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >1</font></span></b><b style="mso-bidi-font-weight:normal" ><span style="font-family:SimSun;mso-ansi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >8</font></span></b><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;mso-ansi-font-weight:bold;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></b></p></td></tr><tr style="height:13.3000pt;" ><td width=213  valign=bottom  nowrap  style="width:106.8500pt;padding:0.0000pt 0.0000pt 0.0000pt 22.7000pt ;border-left:none;
mso-border-left-alt:none;border-right:none;mso-border-right-alt:none;
border-top:none;mso-border-top-alt:1.0000pt solid rgb(255,0,0);border-bottom:1.5000pt solid rgb(255,0,0);
mso-border-bottom-alt:1.5000pt solid rgb(255,0,0);" ><p class=MsoNormal  align=center  style="margin-left:0.4500pt;text-indent:-0.4500pt;text-align:center;" ><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';mso-ansi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></b></p></td></tr><tr style="height:27.6500pt;" ><td width=213  valign=top  rowspan=4  style="width:106.8500pt;padding:0.0000pt 0.0000pt 0.0000pt 22.7000pt ;border-left:none;
mso-border-left-alt:none;border-right:none;mso-border-right-alt:none;
border-top:none;mso-border-top-alt:none;border-bottom:none;
mso-border-bottom-alt:none;" ><p class=MsoNormal  align=center  style="margin-left:0.5500pt;text-indent:-0.5500pt;text-align:center;
line-height:10.0000pt;mso-line-height-rule:exactly;" ><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';mso-ansi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></b></p></td><td width=261  valign=bottom  colspan=4  style="width:130.7000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:none;
mso-border-left-alt:none;border-right:none;mso-border-right-alt:none;
border-top:none;mso-border-top-alt:none;border-bottom:none;
mso-border-bottom-alt:none;" ><p class=MsoNormal  align=center  style="margin-left:0.7500pt;text-indent:-0.7500pt;text-align:center;
line-height:26.0000pt;mso-line-height-rule:exactly;" ><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';mso-ansi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;position:relative;top:3.0000pt;
mso-text-raise:-3.0000pt;" ><font face="SimSun" >审核（定密审核人）</font></span></b><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';mso-ansi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;position:relative;top:3.0000pt;
mso-text-raise:-3.0000pt;" ><o:p></o:p></span></b></p></td><td width=457  valign=bottom  colspan=4  style="width:228.6500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:none;
mso-border-left-alt:none;border-right:none;mso-border-right-alt:none;
border-top:none;mso-border-top-alt:0.7500pt solid rgb(255,0,0);border-bottom:1.0000pt solid rgb(255,0,0);
mso-border-bottom-alt:0.7500pt solid rgb(255,0,0);" ><p class=MsoNormal  align=center  style="text-align:center;line-height:26.0000pt;mso-line-height-rule:exactly;" ><b style="mso-bidi-font-weight:normal" ><span style="font-family:SimSun;mso-ansi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" ><font face="SimSun" >戚保凯</font></span></b><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';mso-ansi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" >20250</span></b><b style="mso-bidi-font-weight:normal" ><span style="font-family:SimSun;mso-ansi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >9</font></span></b><b style="mso-bidi-font-weight:normal" ><span style="font-family:SimSun;mso-ansi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >1</font></span></b><b style="mso-bidi-font-weight:normal" ><span style="font-family:SimSun;mso-ansi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >9</font></span></b><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;mso-ansi-font-weight:bold;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></b></p></td></tr><tr style="height:27.6500pt;" ><td width=261  valign=bottom  colspan=4  style="width:130.7000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:none;
mso-border-left-alt:none;border-right:none;mso-border-right-alt:none;
border-top:none;mso-border-top-alt:none;border-bottom:none;
mso-border-bottom-alt:none;" ><p class=MsoNormal  align=center  style="margin-left:0.7500pt;text-indent:-0.7500pt;text-align:center;
line-height:26.0000pt;mso-line-height-rule:exactly;" ><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';mso-ansi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;position:relative;top:3.0000pt;
mso-text-raise:-3.0000pt;" ><font face="SimSun" >复核</font></span></b><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';mso-ansi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;position:relative;top:3.0000pt;
mso-text-raise:-3.0000pt;" ><o:p></o:p></span></b></p></td><td width=457  valign=bottom  colspan=4  style="width:228.6500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:none;
mso-border-left-alt:none;border-right:none;mso-border-right-alt:none;
border-top:none;mso-border-top-alt:0.7500pt solid rgb(255,0,0);border-bottom:1.0000pt solid rgb(255,0,0);
mso-border-bottom-alt:0.7500pt solid rgb(255,0,0);" ><p class=MsoNormal  align=center  style="text-align:center;line-height:26.0000pt;mso-line-height-rule:exactly;" ><b style="mso-bidi-font-weight:normal" ><span style="font-family:SimSun;mso-ansi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" ><font face="SimSun" >范晓雷</font></span></b><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';mso-ansi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" >20250</span></b><b style="mso-bidi-font-weight:normal" ><span style="font-family:SimSun;mso-ansi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >9</font></span></b><b style="mso-bidi-font-weight:normal" ><span style="font-family:SimSun;mso-ansi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >1</font></span></b><b style="mso-bidi-font-weight:normal" ><span style="font-family:SimSun;mso-ansi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >9</font></span></b><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;mso-ansi-font-weight:bold;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></b></p></td></tr><tr style="height:27.6500pt;" ><td width=261  valign=bottom  colspan=4  style="width:130.7000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:none;
mso-border-left-alt:none;border-right:none;mso-border-right-alt:none;
border-top:none;mso-border-top-alt:none;border-bottom:none;
mso-border-bottom-alt:none;" ><p class=MsoNormal  align=center  style="margin-left:0.7500pt;text-indent:-0.7500pt;text-align:center;
line-height:26.0000pt;mso-line-height-rule:exactly;" ><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';mso-ansi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;position:relative;top:3.0000pt;
mso-text-raise:-3.0000pt;" ><font face="SimSun" >批准（定密批准人）</font></span></b><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';mso-ansi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;position:relative;top:3.0000pt;
mso-text-raise:-3.0000pt;" ><o:p></o:p></span></b></p></td><td width=457  valign=bottom  colspan=4  style="width:228.6500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:none;
mso-border-left-alt:none;border-right:none;mso-border-right-alt:none;
border-top:none;mso-border-top-alt:0.7500pt solid rgb(255,0,0);border-bottom:1.0000pt solid rgb(255,0,0);
mso-border-bottom-alt:0.7500pt solid rgb(255,0,0);" ><p class=MsoNormal  align=center  style="text-align:center;line-height:26.0000pt;mso-line-height-rule:exactly;" ><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';mso-ansi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" ><font face="SimSun" >刘照智</font>20250</span></b><b style="mso-bidi-font-weight:normal" ><span style="font-family:SimSun;mso-ansi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >9</font></span></b><b style="mso-bidi-font-weight:normal" ><span style="font-family:SimSun;mso-ansi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >1</font></span></b><b style="mso-bidi-font-weight:normal" ><span style="font-family:SimSun;mso-ansi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >9</font></span></b><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';mso-ansi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" ><o:p></o:p></span></b></p></td></tr><tr style="height:178.1500pt;" ><td width=888  valign=center  colspan=11  style="width:444.2000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:4.5000pt solid rgb(255,0,0);
mso-border-left-alt:4.5000pt solid rgb(255,0,0);border-right:4.5000pt solid rgb(255,0,0);mso-border-right-alt:4.5000pt solid rgb(255,0,0);
border-top:none;mso-border-top-alt:none;border-bottom:4.5000pt solid rgb(255,0,0);
mso-border-bottom-alt:4.5000pt solid rgb(255,0,0);" ><p class=MsoNormal  align=center  style="margin-top:101.4000pt;margin-left:0.7500pt;mso-para-margin-top:6.5000gd;
text-indent:-0.7500pt;text-align:center;line-height:23.0000pt;
mso-line-height-rule:exactly;" ><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';mso-ansi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:7.5000pt;" ><font face="SimSun" >科技集团公司一院航天爱锐公司</font></span></b><b style="mso-bidi-font-weight:normal" ><span style="font-family:'Times New Roman';mso-ansi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" ><o:p></o:p></span></b></p></td></tr></table></div>
<span style="mso-spacerun:'yes';font-family:'Times New Roman';font-size:14.0000pt;
mso-font-kerning:1.0000pt;" ><br clear=all style='page-break-before:always;mso-break-type:section-break'></span>
<div class="Section1"  style="layout-grid:15.6000pt;" ><p class=286  style="text-indent:21.0000pt;" ><span style="mso-spacerun:'yes';font-family:'Times New Roman';font-size:10.5000pt;
mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></p><h1 style="margin-top:0.0000pt;margin-bottom:0.0000pt;margin-left:21.0000pt;
text-indent:-21.0000pt;tab-stops:left blank 0.0000pt ;line-height:150%;
mso-list:l12 level1 lfo21;" ><a name="_Toc23802" ></a><![if !supportLists]><span style="font-family:SimHei;mso-hansi-font-family:'Times New Roman';mso-bidi-font-family:'Times New Roman';
mso-ansi-font-weight:normal;mso-bidi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:22.0000pt;" ><span style='mso-list:Ignore;' >1　<span>&nbsp;</span></span></span><![endif]><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
mso-ansi-font-weight:normal;mso-bidi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:22.0000pt;" ><font face="SimSun" >概述</font></span><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
mso-ansi-font-weight:normal;mso-bidi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:22.0000pt;" ><o:p></o:p></span></h1><p class=MsoNormal  style="text-indent:24.0000pt;mso-char-indent-count:2.0000;line-height:150%;" ><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >依据</font></span><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
mso-bidi-font-weight:bold;font-size:12.0000pt;mso-font-kerning:1.0000pt;" >Q/Y135-2020<font face="SimSun" >验收要求，对</font></span><u><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
text-decoration:underline;text-underline:single;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" >&nbsp;<font face="SimSun" >增压电磁阀</font></span></u><u><span style="mso-spacerun:'yes';font-family:SimSun;line-height:150%;
text-decoration:underline;text-underline:single;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >XX</font></span></u><u><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
text-decoration:underline;text-underline:single;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" >-0 </span></u><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >产品（以下简称</font><font face="Times New Roman" >“</font><font face="SimSun" >产品</font><font face="Times New Roman" >”</font><font face="SimSun" >）进行质量检查确认。本文重点从产品技术指标满足情况、技术状态变化控制情况、通用质量特性落实情况、生产质量控制情况、质量问题归零及举一反三情况等方面进行分析。</font></span><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p><h1 style="margin-top:0.0000pt;margin-bottom:0.0000pt;margin-left:21.0000pt;
text-indent:-21.0000pt;tab-stops:left blank 0.0000pt ;line-height:150%;
mso-list:l12 level1 lfo21;" ><a name="_Toc32635" ></a><![if !supportLists]><span style="font-family:SimHei;mso-hansi-font-family:'Times New Roman';mso-bidi-font-family:'Times New Roman';
mso-ansi-font-weight:normal;mso-bidi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:22.0000pt;" ><span style='mso-list:Ignore;' >2　<span>&nbsp;</span></span></span><![endif]><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
mso-ansi-font-weight:normal;mso-bidi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:22.0000pt;" ><font face="SimSun" >引用文件</font></span><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
mso-ansi-font-weight:normal;mso-bidi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:22.0000pt;" ><o:p></o:p></span></h1><p class=286  style="text-indent:24.0000pt;line-height:150%;" ><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" >Q/Y135-2020 &nbsp;<font face="SimSun" >型号产品验收管理要求；</font></span><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p><p class=286  style="text-indent:24.0000pt;line-height:150%;" ><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" >Q/Dy1081<font face="SimSun" >《弹（箭）体阀门制造、验收通用技术》；</font></span><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p><p class=286  style="text-indent:24.0000pt;line-height:150%;" ><u><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
text-decoration:underline;text-underline:single;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" >CG0JT10 <font face="SimSun" >增压电磁阀制造、验收技术条件；</font></span></u><u><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
text-decoration:underline;text-underline:single;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" ><o:p></o:p></span></u></p><p class=288  style="margin-left:0.0000pt;mso-para-margin-left:0.0000gd;text-indent:24.0000pt;
mso-char-indent-count:2.0000;tab-stops:left blank 45.3500pt ;text-autospace:ideograph-numeric;
mso-pagination:widow-orphan;" ><u><span style="mso-spacerun:'yes';font-family:SimSun;mso-ascii-font-family:'Times New Roman';
mso-hansi-font-family:'Times New Roman';mso-bidi-font-family:'Times New Roman';text-decoration:underline;
text-underline:single;font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >Dh2JFM110JT1 XX</font><font face="SimSun" >系列通用阀门产品制造验收技术条件</font></span></u><u><span style="mso-spacerun:'yes';font-family:'Times New Roman';mso-fareast-font-family:SimSun;
text-decoration:underline;text-underline:single;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" ><o:p></o:p></span></u></p><h1 style="margin-top:0.0000pt;margin-bottom:0.0000pt;margin-left:21.0000pt;
text-indent:-21.0000pt;tab-stops:left blank 0.0000pt ;line-height:150%;
mso-list:l12 level1 lfo21;" ><a name="_Toc5274" ></a><![if !supportLists]><span style="font-family:SimHei;mso-hansi-font-family:'Times New Roman';mso-bidi-font-family:'Times New Roman';
mso-ansi-font-weight:normal;mso-bidi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:22.0000pt;" ><span style='mso-list:Ignore;' >3　<span>&nbsp;</span></span></span><![endif]><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
mso-ansi-font-weight:normal;mso-bidi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:22.0000pt;" ><font face="SimSun" >研制情况</font></span><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
mso-ansi-font-weight:normal;mso-bidi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:22.0000pt;" ><o:p></o:p></span></h1><h2 style="margin-top:0.0000pt;margin-bottom:0.0000pt;margin-left:21.2000pt;
text-indent:-21.0000pt;tab-stops:left blank 0.0000pt ;line-height:150%;
mso-list:l17 level1 lfo22;" ><a name="_Toc27784" ></a><![if !supportLists]><span style="font-family:SimHei;mso-hansi-font-family:'Times New Roman';mso-bidi-font-family:'Times New Roman';
mso-ansi-font-weight:normal;mso-bidi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" ><span style='mso-list:Ignore;' >3.1　<span>&nbsp;</span></span></span><![endif]><span style="mso-spacerun:'yes';font-family:'Times New Roman';mso-fareast-font-family:SimSun;
line-height:150%;mso-ansi-font-weight:normal;mso-bidi-font-weight:bold;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >单机简介</font></span><span style="mso-spacerun:'yes';font-family:'Times New Roman';mso-fareast-font-family:SimSun;
line-height:150%;mso-ansi-font-weight:normal;mso-bidi-font-weight:bold;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></h2><h3 style="margin-top:0.0000pt;margin-bottom:0.0000pt;line-height:150%;" ><a name="_Toc14157" ></a><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
mso-ansi-font-weight:normal;mso-bidi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" >3.1.1<font face="SimSun" >产品特点</font></span><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
mso-ansi-font-weight:normal;mso-bidi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" ><o:p></o:p></span></h3><p class=MsoNormal  style="text-indent:24.0000pt;mso-char-indent-count:2.0000;line-height:150%;" ><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >产品结构如图</font>1<font face="SimSun" >所示，主要由</font></span><u><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
text-decoration:underline;text-underline:single;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" >&nbsp;<font face="SimSun" >电磁铁</font> </span></u><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >、</font></span><u><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
text-decoration:underline;text-underline:single;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" >&nbsp;<font face="SimSun" >衔铁</font> </span></u><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >、</font></span><u><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
text-decoration:underline;text-underline:single;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" >&nbsp;<font face="SimSun" >壳体</font> </span></u><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >、</font></span><u><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
text-decoration:underline;text-underline:single;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" >&nbsp;<font face="SimSun" >主阀</font></span></u><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >、</font></span><u><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
text-decoration:underline;text-underline:single;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" >&nbsp;<font face="SimSun" >主弹簧</font></span></u><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >、</font></span><u><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
text-decoration:underline;text-underline:single;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" >&nbsp;<font face="SimSun" >副弹簧</font></span></u><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >、</font></span><u><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
text-decoration:underline;text-underline:single;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" >&nbsp;<font face="SimSun" >弹簧座</font></span></u><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >、</font></span><u><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
text-decoration:underline;text-underline:single;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" >&nbsp;<font face="SimSun" >涨圈</font></span></u><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >、</font></span><u><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
text-decoration:underline;text-underline:single;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" >&nbsp;<font face="SimSun" >波纹带</font></span></u><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >、</font></span><u><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
text-decoration:underline;text-underline:single;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" >&nbsp;<font face="SimSun" >压盖</font></span></u><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >等组成。产品工作原理为：</font> </span><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p><p class=MsoNormal  style="text-indent:24.0000pt;mso-char-indent-count:2.0000;line-height:150%;" ><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >控制系统给电磁阀供电，电磁铁（序号</font>1<font face="SimSun" >）受激建立磁场，衔铁（序号</font><font face="Times New Roman" >2</font><font face="SimSun" >）克服气动力和副弹簧（序号</font><font face="Times New Roman" >9</font><font face="SimSun" >）力开启，主阀（序号</font><font face="Times New Roman" >3</font><font face="SimSun" >）背压腔压力释放，主阀（序号</font><font face="Times New Roman" >4</font><font face="SimSun" >）在不平衡面积的气体压差作用下，克服主弹簧（序号</font><font face="Times New Roman" >8</font><font face="SimSun" >）力离开主阀座，电磁阀入口到出口的气体通路打开，即电磁阀打开；控制系统断电，电磁铁受激磁场消失，衔铁（序号</font><font face="Times New Roman" >2</font><font face="SimSun" >）释放，在副弹簧（序号</font><font face="Times New Roman" >9</font><font face="SimSun" >）力作用下回位，主阀（序号</font><font face="Times New Roman" >3</font><font face="SimSun" >）背压腔与排气口的通道关闭，主阀（序号</font><font face="Times New Roman" >3</font><font face="SimSun" >）背压腔建立压力，在主弹簧（序号</font><font face="Times New Roman" >8</font><font face="SimSun" >）和气体压力作用下回位，电磁阀入口与出口的通道关闭，即电磁阀关闭</font></span><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p><p class=279  style="text-indent:0.0000pt;" ><span style="mso-spacerun:'yes';font-family:'Times New Roman';letter-spacing:-0.2000pt;
font-size:10.5000pt;mso-font-kerning:10.5000pt;" ><o:p>&nbsp;</o:p></span></p><p class=279  style="text-indent:0.0000pt;" ><span style="mso-spacerun:'yes';font-family:'Times New Roman';letter-spacing:-0.2000pt;
font-size:10.5000pt;mso-font-kerning:10.5000pt;" ><o:p>&nbsp;</o:p></span></p><p class=305  style="margin-top:0.0000pt;margin-bottom:0.0000pt;margin-left:42.0000pt;
text-indent:-21.2500pt;tab-stops:left blank 30.0000pt ;line-height:150%;
mso-list:l23 level1 lfo23;" ><![if !supportLists]><span style="font-family:SimSun;mso-hansi-font-family:'Times New Roman';mso-ansi-font-weight:normal;
mso-ansi-font-style:normal;font-size:12.0000pt;" ><span style='mso-list:Ignore;' >图1　</span></span><![endif]><span style="mso-spacerun:'yes';font-family:SimSun;mso-ascii-font-family:'Times New Roman';
line-height:150%;font-size:12.0000pt;" ><font face="Times New Roman" >XX</font></span><span style="mso-spacerun:'yes';font-family:'Times New Roman';mso-fareast-font-family:SimSun;
line-height:150%;font-size:12.0000pt;" >-0<font face="SimSun" >产品结构示意图</font></span><span style="mso-spacerun:'yes';font-family:'Times New Roman';mso-fareast-font-family:SimSun;
line-height:150%;font-size:12.0000pt;" ><o:p></o:p></span></p><h3 style="margin-top:0.0000pt;margin-bottom:0.0000pt;line-height:150%;" ><a name="_Toc22020" ></a><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
mso-ansi-font-weight:normal;mso-bidi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" >3.1.2<font face="SimSun" >工艺方案</font></span><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
mso-ansi-font-weight:normal;mso-bidi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" ><o:p></o:p></span></h3><p class=286  style="text-indent:0.0000pt;mso-char-indent-count:0.0000;line-height:150%;" ><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" >(1)<font face="SimSun" >装配流程</font></span><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p><p class=MsoNormal  style="text-indent:24.0000pt;mso-char-indent-count:2.0000;line-height:150%;" ><a name="_Toc85141110" ></a><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >配套、清洗</font><font face="Times New Roman" >→</font><font face="SimSun" >检查</font><font face="Times New Roman" >→</font><font face="SimSun" >螺纹预装配</font><font face="Times New Roman" >→</font><font face="SimSun" >装主壳体部分</font><font face="Times New Roman" >→</font><font face="SimSun" >测量行程间隙</font><font face="Times New Roman" >→</font><font face="SimSun" >装配电磁铁</font><font face="Times New Roman" >→</font><font face="SimSun" >装配其它零组件</font><font face="Times New Roman" >→</font><font face="SimSun" >装保护件。</font></span><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p><p class=286  style="text-indent:0.0000pt;mso-char-indent-count:0.0000;line-height:150%;" ><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" >(2)<font face="SimSun" >试验流程</font></span><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p><p class=MsoNormal  style="text-indent:24.0000pt;mso-char-indent-count:2.0000;line-height:150%;" ><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >试验系统搭建及检查</font><font face="Times New Roman" >→</font><font face="SimSun" >常温性能试验</font><font face="Times New Roman" >→</font><font face="SimSun" >低温性能试验</font><font face="Times New Roman" >→</font><font face="SimSun" >烘干</font><font face="Times New Roman" >→</font><font face="SimSun" >验收级振动试验</font><font face="Times New Roman" >→</font><font face="SimSun" >烘干</font><font face="Times New Roman" >→</font><font face="SimSun" >常温复试</font><font face="Times New Roman" >→</font><font face="SimSun" >高温性能试验（典型试验）</font><font face="Times New Roman" >→</font><font face="SimSun" >常温工作寿命试验（典型试验）</font><font face="Times New Roman" >→</font><font face="SimSun" >烘干</font><font face="Times New Roman" >→</font><font face="SimSun" >低温工作寿命试验（典型试验）</font><font face="Times New Roman" >→</font><font face="SimSun" >烘干</font><font face="Times New Roman" >→</font><font face="SimSun" >真空封存</font><font face="SimSun" >。</font></span><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p><h2 style="margin-top:0.0000pt;margin-bottom:0.0000pt;margin-left:24.0000pt;
text-indent:-24.0000pt;mso-char-indent-count:-2.0000;tab-stops:left blank 0.0000pt ;
line-height:150%;mso-list:l17 level1 lfo22;" ><a name="_Toc22717" ></a><![if !supportLists]><span style="font-family:SimHei;mso-hansi-font-family:'Times New Roman';mso-bidi-font-family:'Times New Roman';
mso-ansi-font-weight:normal;mso-bidi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" ><span style='mso-list:Ignore;' >3.2　<span>&nbsp;</span></span></span><![endif]><span style="mso-spacerun:'yes';font-family:'Times New Roman';mso-fareast-font-family:SimSun;
line-height:150%;mso-ansi-font-weight:normal;mso-bidi-font-weight:bold;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >产品配套情况</font></span><span style="mso-spacerun:'yes';font-family:'Times New Roman';mso-fareast-font-family:SimSun;
line-height:150%;mso-ansi-font-weight:normal;mso-bidi-font-weight:bold;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></h2><p class=279  style="text-indent:23.2000pt;mso-char-indent-count:2.0000;text-align:left;
line-height:150%;" ><a name="_Ref17443" ></a><span style="mso-spacerun:'yes';font-family:SimSun;letter-spacing:-0.2000pt;
font-size:12.0000pt;mso-font-kerning:10.5000pt;" ><a name="_Ref17387" ><font face="SimSun" >本次交付产品同批共生产</font></a></span><span style="mso-spacerun:'yes';font-family:SimSun;letter-spacing:-0.2000pt;
font-size:12.0000pt;mso-font-kerning:10.5000pt;" ><font face="Times New Roman" >49</font></span><span style="mso-spacerun:'yes';font-family:SimSun;letter-spacing:-0.2000pt;
font-size:12.0000pt;mso-font-kerning:10.5000pt;" ><font face="SimSun" >套，</font></span><span style="mso-spacerun:'yes';font-family:SimSun;letter-spacing:-0.2000pt;
font-size:12.0000pt;mso-font-kerning:10.5000pt;" ><font face="SimSun" >第一轮验收试验合格</font></span><span style="mso-spacerun:'yes';font-family:SimSun;letter-spacing:-0.2000pt;
font-size:12.0000pt;mso-font-kerning:10.5000pt;" ><font face="Times New Roman" >40</font><font face="SimSun" >套，</font></span><span style="mso-spacerun:'yes';font-family:SimSun;letter-spacing:-0.2000pt;
font-size:12.0000pt;mso-font-kerning:10.5000pt;" ><font face="SimSun" >典试</font></span><span style="mso-spacerun:'yes';font-family:SimSun;letter-spacing:-0.2000pt;
font-size:12.0000pt;mso-font-kerning:10.5000pt;" ><font face="Times New Roman" >3</font></span><span style="mso-spacerun:'yes';font-family:SimSun;letter-spacing:-0.2000pt;
font-size:12.0000pt;mso-font-kerning:10.5000pt;" ><font face="SimSun" >套，可交付</font></span><span style="mso-spacerun:'yes';font-family:SimSun;letter-spacing:-0.2000pt;
font-size:12.0000pt;mso-font-kerning:10.5000pt;" ><font face="Times New Roman" >37</font></span><span style="mso-spacerun:'yes';font-family:SimSun;letter-spacing:-0.2000pt;
font-size:12.0000pt;mso-font-kerning:10.5000pt;" ><font face="SimSun" >套。详</font></span><span style="mso-spacerun:'yes';font-family:'Times New Roman';letter-spacing:-0.2000pt;
font-size:12.0000pt;mso-font-kerning:10.5000pt;" ><font face="SimSun" >见表</font>1<font face="SimSun" >。</font></span><span style="mso-spacerun:'yes';font-family:SimSun;letter-spacing:-0.2000pt;
font-size:12.0000pt;mso-font-kerning:10.5000pt;" ><o:p></o:p></span></p></div>
<span style="mso-spacerun:'yes';font-family:'Times New Roman';letter-spacing:-0.2000pt;
font-size:12.0000pt;mso-font-kerning:10.5000pt;" ><br clear=all style='page-break-before:always;mso-break-type:section-break'></span>
<div class="Section2"  style="layout-grid:15.6000pt;" ><p class=279  style="text-indent:0.0000pt;text-align:left;line-height:150%;" ><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
letter-spacing:-0.2000pt;font-size:11.0000pt;mso-font-kerning:10.5000pt;" ><o:p>&nbsp;</o:p></span></p><p class=MsoNormal  align=center  style="text-align:center;" ><span style="mso-spacerun:'yes';font-family:'Times New Roman';font-size:10.5000pt;
mso-font-kerning:1.0000pt;" ><font face="SimSun" >表</font> </span><span><span style="mso-spacerun:'yes';font-family:'Times New Roman';font-size:10.5000pt;
mso-font-kerning:1.0000pt;" >1</span></span><span style="mso-spacerun:'yes';font-family:'Times New Roman';font-size:10.5000pt;
mso-font-kerning:1.0000pt;" ><font face="SimSun" >产品交付情况</font></span><span style="mso-spacerun:'yes';font-family:'Times New Roman';font-size:10.5000pt;
mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p><table class=MsoNormalTable  border=1  cellspacing=0  style="border-collapse:collapse;width:100.0000%;mso-table-layout-alt:fixed;
border:none;mso-border-left-alt:1.0000pt solid windowtext;mso-border-top-alt:1.0000pt solid windowtext;
mso-border-right-alt:1.0000pt solid windowtext;mso-border-bottom-alt:1.0000pt solid windowtext;mso-border-insideh:0.5000pt solid windowtext;
mso-border-insidev:0.5000pt solid windowtext;mso-padding-alt:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;" ><tr style="height:62.5000pt;" ><td width=33  valign=center  style="width:16.5000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:1.0000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:1.0000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="text-align:center;line-height:12.0000pt;mso-line-height-rule:exactly;" ><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >序号</font></span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=98  valign=center  style="width:49.1500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:1.0000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="text-align:center;line-height:12.0000pt;mso-line-height-rule:exactly;" ><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >产品名称</font></span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=103  valign=center  style="width:51.9000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:1.0000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="text-align:center;line-height:12.0000pt;mso-line-height-rule:exactly;" ><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >产品图号</font></span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=352  valign=center  style="width:176.2500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:1.0000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="text-align:center;line-height:12.0000pt;mso-line-height-rule:exactly;" ><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >产品编号（不含典试件）</font></span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=103  valign=center  style="width:51.9000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:1.0000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="text-align:center;line-height:12.0000pt;mso-line-height-rule:exactly;" ><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >交付数量</font></span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=124  valign=center  style="width:62.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:1.0000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="text-align:center;line-height:12.0000pt;mso-line-height-rule:exactly;" ><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >开工日期</font></span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=127  valign=center  style="width:63.9500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:1.0000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="text-align:center;line-height:12.0000pt;mso-line-height-rule:exactly;" ><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >完工日期</font></span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=113  valign=center  style="width:56.6500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:1.0000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="text-align:center;line-height:12.0000pt;mso-line-height-rule:exactly;" ><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >质控卡编号</font></span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=97  valign=center  style="width:48.8000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:1.0000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="text-align:center;line-height:12.0000pt;mso-line-height-rule:exactly;" ><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >非金属有效期</font></span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=67  valign=center  style="width:33.5500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:1.0000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="text-align:center;line-height:12.0000pt;mso-line-height-rule:exactly;" ><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >评审日期</font></span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=71  valign=center  style="width:35.6500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:1.0000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="text-align:center;line-height:12.0000pt;mso-line-height-rule:exactly;" ><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >评审报告编号</font></span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=71  valign=center  style="width:35.7000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:1.0000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="text-align:center;line-height:12.0000pt;mso-line-height-rule:exactly;" ><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></p></td><td width=109  valign=center  style="width:54.5500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:1.0000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:1.0000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="text-align:center;line-height:12.0000pt;mso-line-height-rule:exactly;" ><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >备注</font></span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td></tr><tr style="height:4.5000pt;" ><td width=33  valign=center  rowspan=4  style="width:16.5000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:1.0000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="margin-left:21.0000pt;text-indent:-21.0000pt;text-align:center;
line-height:12.0000pt;mso-line-height-rule:exactly;mso-list:l15 level1 lfo24;" ><![if !supportLists]><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><span style='mso-list:Ignore;' >1.<span>&nbsp;</span></span></span><![endif]><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><a name="_Toc24617" ><o:p></o:p></a></span></p></td><td width=98  valign=center  rowspan=4  style="width:49.1500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  style="line-height:15.0000pt;mso-line-height-rule:exactly;" ><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >增压电磁阀</font></span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=103  valign=center  rowspan=4  style="width:51.9000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  style="line-height:15.0000pt;mso-line-height-rule:exactly;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >XX</font></span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" >-0</span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=352  valign=center  style="width:176.2500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  style="line-height:150%;" ><span style="font-family:SimSun;mso-ascii-font-family:'Times New Roman';mso-hansi-font-family:'Times New Roman';
mso-bidi-font-family:'Times New Roman';font-style:normal;font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><font face="Times New Roman" ><span class="dynamic-data" data-source-id="PROD-15224">15224</span>/<span class="dynamic-data" data-source-id="PROD-20024">20024</span>/22024/22124/23124/26223/26323</font></span><span style="font-family:SimSun;mso-bidi-font-family:'Times New Roman';font-style:normal;
font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="Times New Roman" >/27123</font></span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;font-style:normal;
font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=103  valign=center  style="width:51.9000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="text-align:center;line-height:12.0000pt;mso-line-height-rule:exactly;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >8</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=124  valign=center  rowspan=4  style="width:62.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  style="line-height:12.0000pt;mso-line-height-rule:exactly;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >20250</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >822</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=127  valign=center  rowspan=4  style="width:63.9500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  style="line-height:12.0000pt;mso-line-height-rule:exactly;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >20250922</font></span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=113  valign=center  rowspan=4  style="width:56.6500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=279  style="text-indent:0.0000pt;mso-char-indent-count:0.0000;text-align:left;" ><span style="font-family:SimSun;letter-spacing:-0.2000pt;font-size:10.5000pt;
mso-font-kerning:10.5000pt;" ><font face="Times New Roman" >1325002587</font></span><span style="font-family:SimSun;letter-spacing:-0.2000pt;font-size:10.5000pt;
mso-font-kerning:10.5000pt;" ><o:p></o:p></span></p></td><td width=97  valign=center  rowspan=4  style="width:48.8000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  style="line-height:12.0000pt;mso-line-height-rule:exactly;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >20311103</font></span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;font-size:10.5000pt;
mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=67  valign=center  rowspan=4  style="width:33.5500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  style="line-height:12.0000pt;mso-line-height-rule:exactly;" ><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></p></td><td width=71  valign=center  rowspan=4  style="width:35.6500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  style="line-height:12.0000pt;mso-line-height-rule:exactly;" ><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></p></td><td width=71  valign=center  style="width:35.7000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  style="line-height:12.0000pt;mso-line-height-rule:exactly;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >/</font></span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=109  valign=center  rowspan=4  style="width:54.5500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:1.0000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=279  style="text-indent:0.0000pt;text-align:left;line-height:150%;" ><span style="font-family:SimSun;letter-spacing:-0.2000pt;font-size:10.5000pt;
mso-font-kerning:10.5000pt;" ><font face="SimSun" >典试件：</font><font face="Times New Roman" >22424</font><font face="SimSun" >、</font><font face="Times New Roman" >26224</font><font face="SimSun" >、</font><font face="Times New Roman" >38223</font></span><span style="font-family:SimSun;letter-spacing:-0.2000pt;font-size:10.5000pt;
mso-font-kerning:10.5000pt;" ><o:p></o:p></span></p></td></tr><tr style="height:4.5000pt;" ><td width=352  valign=center  style="width:176.2500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  style="line-height:150%;" ><span style="font-family:SimSun;mso-ascii-font-family:'Times New Roman';mso-hansi-font-family:'Times New Roman';
mso-bidi-font-family:'Times New Roman';font-style:normal;font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><font face="Times New Roman" >22323/24923/32523/32923/33923/34223/36123/36223/37323/37623 <span style="font-family:'Times New Roman';mso-spacerun:'yes';" >&nbsp;</font></span></span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;font-style:normal;
font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=103  valign=center  style="width:51.9000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="text-align:center;line-height:12.0000pt;mso-line-height-rule:exactly;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >10</font></span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=71  valign=center  style="width:35.7000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  style="line-height:12.0000pt;mso-line-height-rule:exactly;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >/</font></span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td></tr><tr style="height:4.5000pt;" ><td width=352  valign=center  style="width:176.2500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  style="line-height:150%;" ><span style="font-family:SimSun;mso-ascii-font-family:'Times New Roman';mso-hansi-font-family:'Times New Roman';
mso-bidi-font-family:'Times New Roman';font-style:normal;font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><font face="Times New Roman" ><span class="dynamic-data" data-source-id="PROD-24324">24324</span>/<span class="dynamic-data" data-source-id="PROD-24724">24724</span>/<span class="dynamic-data" data-source-id="PROD-24824">24824</span>/25024/25624/27824/33524/33824/34124/34524/35124/35824/36024/36124/37424/37524/37624/37724</font></span><span style="font-family:SimSun;mso-ascii-font-family:'Times New Roman';mso-hansi-font-family:'Times New Roman';
mso-bidi-font-family:'Times New Roman';font-style:normal;font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=103  valign=center  style="width:51.9000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="text-align:center;line-height:12.0000pt;mso-line-height-rule:exactly;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >18</font></span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=71  valign=center  style="width:35.7000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  style="line-height:12.0000pt;mso-line-height-rule:exactly;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >/</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td></tr><tr style="height:33.5500pt;" ><td width=352  valign=center  style="width:176.2500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:1.0000pt solid windowtext;" ><p class=MsoNormal  style="line-height:150%;" ><span style="font-family:SimSun;mso-ascii-font-family:'Times New Roman';mso-hansi-font-family:'Times New Roman';
mso-bidi-font-family:'Times New Roman';font-style:normal;font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><font face="Times New Roman" >8424</font></span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;font-style:normal;
font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=103  valign=center  style="width:51.9000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:1.0000pt solid windowtext;" ><p class=MsoNormal  align=center  style="text-align:center;line-height:12.0000pt;mso-line-height-rule:exactly;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >1</font></span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=71  valign=center  style="width:35.7000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:1.0000pt solid windowtext;" ><p class=MsoNormal  style="line-height:12.0000pt;mso-line-height-rule:exactly;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;
background:rgb(255,255,0);mso-highlight:rgb(255,255,0);" ><font face="Times New Roman" >/</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;
background:rgb(255,255,0);mso-highlight:rgb(255,255,0);" ><o:p></o:p></span></p></td></tr></table><h1 style="margin-top:6.0000pt;margin-bottom:0.0000pt;margin-left:21.0000pt;
mso-para-margin-top:0.5000gd;text-indent:-21.0000pt;tab-stops:left blank 0.0000pt ;
line-height:150%;mso-list:l12 level1 lfo21;" ><![if !supportLists]><span style="font-family:SimHei;mso-hansi-font-family:'Times New Roman';mso-bidi-font-family:'Times New Roman';
mso-ansi-font-weight:normal;mso-bidi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:22.0000pt;" ><span style='mso-list:Ignore;' >4　<span>&nbsp;</span></span></span><![endif]><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
mso-ansi-font-weight:normal;mso-bidi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:22.0000pt;" ><font face="SimSun" >产品技术指标满足设计要求情况</font></span><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
mso-ansi-font-weight:normal;mso-bidi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:22.0000pt;" ><o:p></o:p></span></h1><p class=MsoNormalIndent  style="text-indent:24.0000pt;line-height:150%;" ><u><span style="mso-spacerun:'yes';font-family:SimSun;line-height:150%;
text-decoration:underline;text-underline:single;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >XX</font></span></u><u><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
text-decoration:underline;text-underline:single;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" >-0<font face="SimSun" >增压电磁阀</font></span></u><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >产品按设计文件要求对设计重点关注的检测和试验项目、检测和试验内容、设计要求及实际检测结果进行确认。</font></span><span style="mso-spacerun:'yes';font-family:SimSun;line-height:150%;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p><p class=MsoNormal  style="text-indent:24.0000pt;mso-char-indent-count:2.0000;line-height:150%;" ><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >经复查确认，产品的各项设计关注检测项目、试验项目的测量结果均符合设计文件要求。</font></span></p></div>
<span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><br clear=all style='page-break-before:always;mso-break-type:section-break'></span>
<div class="Section3"  style="layout-grid:15.6000pt;" ><p class=MsoNormal  style="text-indent:24.0000pt;mso-char-indent-count:2.0000;line-height:150%;" ><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p><h1 style="margin-top:0.0000pt;margin-bottom:0.0000pt;margin-left:21.0000pt;
text-indent:-21.0000pt;tab-stops:left blank 0.0000pt ;line-height:150%;
mso-list:l12 level1 lfo21;" ><a name="_Toc22157" ></a><![if !supportLists]><span style="font-family:SimHei;mso-hansi-font-family:'Times New Roman';mso-bidi-font-family:'Times New Roman';
mso-ansi-font-weight:normal;mso-bidi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:22.0000pt;" ><span style='mso-list:Ignore;' >5　<span>&nbsp;</span></span></span><![endif]><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
mso-ansi-font-weight:normal;mso-bidi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:22.0000pt;" ><font face="SimSun" >型号技术状态的符合性</font></span><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
mso-ansi-font-weight:normal;mso-bidi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:22.0000pt;" ><o:p></o:p></span></h1><h2 style="margin-top:0.0000pt;margin-bottom:0.0000pt;margin-left:21.0000pt;
text-indent:-21.0000pt;tab-stops:left blank 0.0000pt ;line-height:150%;
mso-list:l18 level1 lfo25;" ><a name="_Toc23321" ></a><![if !supportLists]><span style="font-family:SimHei;mso-hansi-font-family:'Times New Roman';mso-bidi-font-family:'Times New Roman';
mso-ansi-font-weight:normal;mso-bidi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" ><span style='mso-list:Ignore;' >5.1　<span>&nbsp;</span></span></span><![endif]><span style="mso-spacerun:'yes';font-family:'Times New Roman';mso-fareast-font-family:SimSun;
line-height:150%;mso-ansi-font-weight:normal;mso-bidi-font-weight:bold;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >技术状态基线与变化统计</font></span><span style="mso-spacerun:'yes';font-family:'Times New Roman';mso-fareast-font-family:SimSun;
line-height:150%;mso-ansi-font-weight:normal;mso-bidi-font-weight:bold;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></h2><p class=MsoNormal  style="text-indent:24.0000pt;mso-char-indent-count:2.0000;line-height:150%;" ><span style="mso-spacerun:'yes';font-family:SimSun;line-height:150%;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >无技术状态变化</font></span><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >。</font></span><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p><h2 style="margin-top:0.0000pt;margin-bottom:0.0000pt;margin-left:21.0000pt;
text-indent:-21.0000pt;tab-stops:left blank 0.0000pt ;line-height:150%;
mso-list:l18 level1 lfo25;" ><a name="_Toc11578" ></a><![if !supportLists]><span style="font-family:SimHei;mso-hansi-font-family:'Times New Roman';mso-bidi-font-family:'Times New Roman';
font-weight:normal;font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><span style='mso-list:Ignore;' >5.2　<span>&nbsp;</span></span></span><![endif]><span style="mso-spacerun:'yes';font-family:'Times New Roman';mso-fareast-font-family:SimSun;
line-height:150%;font-weight:normal;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" ><font face="SimSun" >技术状态变化落实情况</font></span><span style="mso-spacerun:'yes';font-family:'Times New Roman';mso-fareast-font-family:SimSun;
line-height:150%;font-weight:normal;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" ><o:p></o:p></span></h2><p class=MsoNormal  style="text-indent:24.0000pt;mso-char-indent-count:2.0000;line-height:150%;" ><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >产品在生产过程中，设计下发偏离单</font></span><span style="mso-spacerun:'yes';font-family:SimSun;line-height:150%;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >3</font><font face="SimSun" >份</font></span><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >、</font></span><span style="mso-spacerun:'yes';font-family:SimSun;line-height:150%;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >未</font></span><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >下发更改单、公司下发工艺通知单</font> 0 <font face="SimSun" >份。经复查确认，偏离单内容及要求均已落实艺文件和产品上。具体情况见附表</font><font face="Times New Roman" >1</font><font face="SimSun" >《偏离单落实情况统计表》，附表</font><font face="Times New Roman" >2</font><font face="SimSun" >《更改单落实情况统计表》。</font><a name="_Toc7432" ></a></span><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p><h2 style="margin-top:0.0000pt;margin-bottom:0.0000pt;margin-left:21.0000pt;
text-indent:-21.0000pt;tab-stops:left blank 0.0000pt ;line-height:150%;
mso-list:l18 level1 lfo25;" ><![if !supportLists]><span style="font-family:SimHei;mso-hansi-font-family:'Times New Roman';mso-bidi-font-family:'Times New Roman';
mso-ansi-font-weight:normal;mso-bidi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" ><span style='mso-list:Ignore;' >5.3　<span>&nbsp;</span></span></span><![endif]><span style="mso-spacerun:'yes';font-family:'Times New Roman';mso-fareast-font-family:SimSun;
line-height:150%;mso-ansi-font-weight:normal;mso-bidi-font-weight:bold;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >偏离及超差情况（含代料情况）</font></span><span style="mso-spacerun:'yes';font-family:'Times New Roman';mso-fareast-font-family:SimSun;
line-height:150%;mso-ansi-font-weight:normal;mso-bidi-font-weight:bold;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></h2><p class=MsoNormal  style="text-indent:24.0000pt;mso-char-indent-count:2.0000;line-height:150%;" ><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >产品在生产过程中，办理质疑单</font></span><span style="mso-spacerun:'yes';font-family:SimSun;line-height:150%;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >1</font><font face="SimSun" >份</font></span><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >。具体内容见附表</font>3<font face="SimSun" >《产品超差情况汇总表》，</font></span><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p><p class=MsoNormal  style="line-height:150%;" ><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >附表</font>4<font face="SimSun" >《原材料代料情况汇总表》。</font></span><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p><p class=MsoNormal  style="text-indent:24.0000pt;mso-char-indent-count:2.0000;line-height:150%;" ><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >质疑单办理的超差原因分类统计如下（单位：条）：</font></span><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p><table class=MsoNormalTable  border=1  cellspacing=0  style="border-collapse:collapse;mso-table-layout-alt:fixed;border:none;
mso-border-left-alt:1.0000pt solid windowtext;mso-border-top-alt:1.0000pt solid windowtext;mso-border-right-alt:1.0000pt solid windowtext;
mso-border-bottom-alt:1.0000pt solid windowtext;mso-border-insideh:0.5000pt solid windowtext;mso-border-insidev:0.5000pt solid windowtext;
mso-padding-alt:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;" ><tr style="height:25.5000pt;page-break-inside:avoid;" ><td width=132  valign=center  style="width:66.2500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:1.0000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:1.0000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="text-align:center;line-height:12.0000pt;mso-line-height-rule:exactly;" ><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >原因分类</font></span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=90  valign=center  style="width:45.0000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:1.0000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="margin-right:-5.2500pt;margin-left:-5.2500pt;mso-para-margin-right:-0.5000gd;
mso-para-margin-left:-0.5000gd;text-align:center;line-height:12.0000pt;
mso-line-height-rule:exactly;" ><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >设计</font></span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=90  valign=center  style="width:45.0000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:1.0000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="margin-right:-5.2500pt;margin-left:-5.2500pt;mso-para-margin-right:-0.5000gd;
mso-para-margin-left:-0.5000gd;text-align:center;line-height:12.0000pt;
mso-line-height-rule:exactly;" ><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >工艺</font></span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=89  valign=center  style="width:44.9500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:1.0000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="margin-right:-5.2500pt;margin-left:-5.2500pt;mso-para-margin-right:-0.5000gd;
mso-para-margin-left:-0.5000gd;text-align:center;line-height:12.0000pt;
mso-line-height-rule:exactly;" ><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >操作</font></span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=90  valign=center  style="width:45.0000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:1.0000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="margin-right:-5.2500pt;margin-left:-5.2500pt;mso-para-margin-right:-0.5000gd;
mso-para-margin-left:-0.5000gd;text-align:center;line-height:12.0000pt;
mso-line-height-rule:exactly;" ><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >设备</font></span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=89  valign=center  style="width:44.9500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:1.0000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="margin-right:-5.2500pt;margin-left:-5.2500pt;mso-para-margin-right:-0.5000gd;
mso-para-margin-left:-0.5000gd;text-align:center;line-height:12.0000pt;
mso-line-height-rule:exactly;" ><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >原材料</font></span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=90  valign=center  style="width:45.0000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:1.0000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="margin-right:-5.2500pt;margin-left:-5.2500pt;mso-para-margin-right:-0.5000gd;
mso-para-margin-left:-0.5000gd;text-align:center;line-height:12.0000pt;
mso-line-height-rule:exactly;" ><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >管理</font></span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=89  valign=center  style="width:44.9500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:1.0000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="margin-right:-5.2500pt;margin-left:-5.2500pt;mso-para-margin-right:-0.5000gd;
mso-para-margin-left:-0.5000gd;text-align:center;line-height:12.0000pt;
mso-line-height-rule:exactly;" ><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >其它</font></span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=90  valign=center  style="width:45.0000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:1.0000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:1.0000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="margin-right:-5.2500pt;margin-left:-5.2500pt;mso-para-margin-right:-0.5000gd;
mso-para-margin-left:-0.5000gd;text-align:center;line-height:12.0000pt;
mso-line-height-rule:exactly;" ><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >合计</font></span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td></tr><tr style="height:25.5000pt;page-break-inside:avoid;" ><td width=132  valign=center  style="width:66.2500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:1.0000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:1.0000pt solid windowtext;" ><p class=MsoNormal  align=center  style="text-align:center;line-height:12.0000pt;mso-line-height-rule:exactly;" ><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >超差条数</font></span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=90  valign=center  style="width:45.0000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:1.0000pt solid windowtext;" ><p class=MsoNormal  align=center  style="margin-right:-9.3500pt;mso-para-margin-right:-0.8900gd;text-align:center;
line-height:12.0000pt;mso-line-height-rule:exactly;" ><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" >0</span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=90  valign=center  style="width:45.0000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:1.0000pt solid windowtext;" ><p class=MsoNormal  align=center  style="margin-right:-9.3500pt;mso-para-margin-right:-0.8900gd;text-align:center;
line-height:12.0000pt;mso-line-height-rule:exactly;" ><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" >0</span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=89  valign=center  style="width:44.9500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:1.0000pt solid windowtext;" ><p class=MsoNormal  align=center  style="margin-right:-9.3500pt;mso-para-margin-right:-0.8900gd;text-align:center;
line-height:12.0000pt;mso-line-height-rule:exactly;" ><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" >0</span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=90  valign=center  style="width:45.0000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:1.0000pt solid windowtext;" ><p class=MsoNormal  align=center  style="margin-right:-9.3500pt;mso-para-margin-right:-0.8900gd;text-align:center;
line-height:12.0000pt;mso-line-height-rule:exactly;" ><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" >0</span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=89  valign=center  style="width:44.9500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:1.0000pt solid windowtext;" ><p class=MsoNormal  align=center  style="margin-right:-9.3500pt;mso-para-margin-right:-0.8900gd;text-align:center;
line-height:12.0000pt;mso-line-height-rule:exactly;" ><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" >0</span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=90  valign=center  style="width:45.0000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:1.0000pt solid windowtext;" ><p class=MsoNormal  align=center  style="margin-right:-9.3500pt;mso-para-margin-right:-0.8900gd;text-align:center;
line-height:12.0000pt;mso-line-height-rule:exactly;" ><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" >0</span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=89  valign=center  style="width:44.9500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:1.0000pt solid windowtext;" ><p class=MsoNormal  align=center  style="margin-right:-9.3500pt;mso-para-margin-right:-0.8900gd;text-align:center;
line-height:12.0000pt;mso-line-height-rule:exactly;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >1</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=90  valign=center  style="width:45.0000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:1.0000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:1.0000pt solid windowtext;" ><p class=MsoNormal  align=center  style="margin-right:-9.3500pt;mso-para-margin-right:-0.8900gd;text-align:center;
line-height:12.0000pt;mso-line-height-rule:exactly;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >1</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td></tr></table><h1 style="margin-top:0.0000pt;margin-bottom:0.0000pt;margin-left:21.0000pt;
text-indent:-21.0000pt;tab-stops:left blank 0.0000pt ;line-height:150%;
mso-list:l12 level1 lfo21;" ><a name="_Toc8804" ></a><![if !supportLists]><span style="font-family:SimHei;mso-hansi-font-family:'Times New Roman';mso-bidi-font-family:'Times New Roman';
mso-ansi-font-weight:normal;mso-bidi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:22.0000pt;" ><span style='mso-list:Ignore;' >6　<span>&nbsp;</span></span></span><![endif]><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
mso-ansi-font-weight:normal;mso-bidi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:22.0000pt;" ><font face="SimSun" >通用质量特性研制落实情况</font></span><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
mso-ansi-font-weight:normal;mso-bidi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:22.0000pt;" ><o:p></o:p></span></h1><h2 style="margin-top:0.0000pt;margin-bottom:0.0000pt;margin-left:21.0000pt;
text-indent:-21.0000pt;tab-stops:left blank 0.0000pt ;line-height:150%;
mso-list:l19 level1 lfo11;" ><a name="_Toc26473" ></a><![if !supportLists]><span style="font-family:SimHei;mso-hansi-font-family:'Times New Roman';mso-bidi-font-family:'Times New Roman';
mso-ansi-font-weight:normal;mso-bidi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" ><span style='mso-list:Ignore;' >6.1　<span>&nbsp;</span></span></span><![endif]><span style="mso-spacerun:'yes';font-family:'Times New Roman';mso-fareast-font-family:SimSun;
line-height:150%;mso-ansi-font-weight:normal;mso-bidi-font-weight:bold;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >可靠性落实情况</font></span><span style="mso-spacerun:'yes';font-family:'Times New Roman';mso-fareast-font-family:SimSun;
line-height:150%;mso-ansi-font-weight:normal;mso-bidi-font-weight:bold;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></h2><p class=MsoNormal  style="text-indent:24.0000pt;mso-char-indent-count:2.0000;line-height:150%;" ><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >不涉及。</font></span><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p><h2 style="margin-top:0.0000pt;margin-bottom:0.0000pt;margin-left:21.0000pt;
text-indent:-21.0000pt;tab-stops:left blank 0.0000pt ;line-height:150%;
mso-list:l19 level1 lfo11;" ><a name="_Toc4928" ></a><![if !supportLists]><span style="font-family:SimHei;mso-hansi-font-family:'Times New Roman';mso-bidi-font-family:'Times New Roman';
mso-ansi-font-weight:normal;mso-bidi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" ><span style='mso-list:Ignore;' >6.2　<span>&nbsp;</span></span></span><![endif]><span style="mso-spacerun:'yes';font-family:'Times New Roman';mso-fareast-font-family:SimSun;
line-height:150%;mso-ansi-font-weight:normal;mso-bidi-font-weight:bold;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >安全性落实情况</font></span><span style="mso-spacerun:'yes';font-family:'Times New Roman';mso-fareast-font-family:SimSun;
line-height:150%;mso-ansi-font-weight:normal;mso-bidi-font-weight:bold;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></h2><p class=MsoNormal  style="text-indent:24.0000pt;mso-char-indent-count:2.0000;line-height:150%;" ><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >不涉及</font><a name="_Toc28794" ><font face="SimSun" >。</font></a></span><b style="mso-bidi-font-weight:normal" ><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
mso-ansi-font-weight:bold;font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></b></p><h2 style="margin-top:0.0000pt;margin-bottom:0.0000pt;margin-left:21.0000pt;
text-indent:-21.0000pt;tab-stops:left blank 0.0000pt ;line-height:150%;
mso-list:l19 level1 lfo11;" ><![if !supportLists]><span style="font-family:SimHei;mso-hansi-font-family:'Times New Roman';mso-bidi-font-family:'Times New Roman';
mso-ansi-font-weight:normal;mso-bidi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" ><span style='mso-list:Ignore;' >6.3　<span>&nbsp;</span></span></span><![endif]><span style="mso-spacerun:'yes';font-family:'Times New Roman';mso-fareast-font-family:SimSun;
line-height:150%;mso-ansi-font-weight:normal;mso-bidi-font-weight:bold;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >维修性落实情况</font></span><span style="mso-spacerun:'yes';font-family:'Times New Roman';mso-fareast-font-family:SimSun;
line-height:150%;mso-ansi-font-weight:normal;mso-bidi-font-weight:bold;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></h2><p class=MsoNormal  style="text-indent:24.0000pt;mso-char-indent-count:2.0000;line-height:150%;" ><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >不涉及。</font></span><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p><h2 style="margin-top:0.0000pt;margin-bottom:0.0000pt;margin-left:21.0000pt;
text-indent:-21.0000pt;tab-stops:left blank 0.0000pt ;line-height:150%;
mso-list:l19 level1 lfo11;" ><a name="_Toc573" ></a><![if !supportLists]><span style="font-family:SimHei;mso-hansi-font-family:'Times New Roman';mso-bidi-font-family:'Times New Roman';
mso-ansi-font-weight:normal;mso-bidi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" ><span style='mso-list:Ignore;' >6.4　<span>&nbsp;</span></span></span><![endif]><span style="mso-spacerun:'yes';font-family:'Times New Roman';mso-fareast-font-family:SimSun;
line-height:150%;mso-ansi-font-weight:normal;mso-bidi-font-weight:bold;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >测试性落实情况</font></span><span style="mso-spacerun:'yes';font-family:'Times New Roman';mso-fareast-font-family:SimSun;
line-height:150%;mso-ansi-font-weight:normal;mso-bidi-font-weight:bold;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></h2><p class=MsoNormal  style="text-indent:24.0000pt;mso-char-indent-count:2.0000;line-height:150%;" ><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >不涉及。</font></span><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p><h2 style="margin-top:0.0000pt;margin-bottom:0.0000pt;margin-left:21.0000pt;
text-indent:-21.0000pt;tab-stops:left blank 0.0000pt ;line-height:150%;
mso-list:l19 level1 lfo11;" ><a name="_Toc11660" ></a><![if !supportLists]><span style="font-family:SimHei;mso-hansi-font-family:'Times New Roman';mso-bidi-font-family:'Times New Roman';
mso-ansi-font-weight:normal;mso-bidi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" ><span style='mso-list:Ignore;' >6.5　<span>&nbsp;</span></span></span><![endif]><span style="mso-spacerun:'yes';font-family:'Times New Roman';mso-fareast-font-family:SimSun;
line-height:150%;mso-ansi-font-weight:normal;mso-bidi-font-weight:bold;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >保障性落实情况</font></span><span style="mso-spacerun:'yes';font-family:'Times New Roman';mso-fareast-font-family:SimSun;
line-height:150%;mso-ansi-font-weight:normal;mso-bidi-font-weight:bold;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></h2><p class=MsoNormal  style="text-indent:24.0000pt;mso-char-indent-count:2.0000;line-height:150%;" ><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >不涉及。</font></span><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p><h2 style="margin-top:0.0000pt;margin-bottom:0.0000pt;margin-left:21.0000pt;
text-indent:-21.0000pt;tab-stops:left blank 0.0000pt ;line-height:150%;
mso-list:l19 level1 lfo11;" ><a name="_Toc13063" ></a><![if !supportLists]><span style="font-family:SimHei;mso-hansi-font-family:'Times New Roman';mso-bidi-font-family:'Times New Roman';
mso-ansi-font-weight:normal;mso-bidi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" ><span style='mso-list:Ignore;' >6.6　<span>&nbsp;</span></span></span><![endif]><span style="mso-spacerun:'yes';font-family:'Times New Roman';mso-fareast-font-family:SimSun;
line-height:150%;mso-ansi-font-weight:normal;mso-bidi-font-weight:bold;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >环境适应性落实情况</font></span><span style="mso-spacerun:'yes';font-family:'Times New Roman';mso-fareast-font-family:SimSun;
line-height:150%;mso-ansi-font-weight:normal;mso-bidi-font-weight:bold;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></h2><p class=MsoNormal  style="text-indent:24.0000pt;mso-char-indent-count:2.0000;line-height:150%;" ><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >不涉及。</font></span><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p><h2 style="margin-top:0.0000pt;margin-bottom:0.0000pt;margin-left:21.0000pt;
text-indent:-21.0000pt;tab-stops:left blank 0.0000pt ;line-height:150%;
mso-list:l19 level1 lfo11;" ><a name="_Toc20692" ></a><![if !supportLists]><span style="font-family:SimHei;mso-hansi-font-family:'Times New Roman';mso-bidi-font-family:'Times New Roman';
mso-ansi-font-weight:normal;mso-bidi-font-weight:bold;font-size:12.0000pt;
mso-font-kerning:1.0000pt;" ><span style='mso-list:Ignore;' >6.7　<span>&nbsp;</span></span></span><![endif]><span style="mso-spacerun:'yes';font-family:'Times New Roman';mso-fareast-font-family:SimSun;
line-height:150%;mso-ansi-font-weight:normal;mso-bidi-font-weight:bold;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >电磁兼容性落实情况</font></span><span style="mso-spacerun:'yes';font-family:'Times New Roman';mso-fareast-font-family:SimSun;
line-height:150%;mso-ansi-font-weight:normal;mso-bidi-font-weight:bold;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></h2><p class=MsoNormal  style="text-indent:24.0000pt;mso-char-indent-count:2.0000;line-height:150%;" ><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >不涉及。</font></span><span style="mso-spacerun:'yes';font-family:'Times New Roman';line-height:150%;
font-size:12.0000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p><p class=MsoNormal  style="line-height:150%;" ><span style="mso-spacerun:'yes';font-family:'Times New Roman';mso-fareast-font-family:SimHei;
font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></p><p class=MsoNormal  style="line-height:150%;" ><span style="mso-spacerun:'yes';font-family:'Times New Roman';mso-fareast-font-family:SimHei;
font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimHei" >附表</font>A.1</span><span style="mso-spacerun:'yes';font-family:SimHei;font-size:10.5000pt;
mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >2.18</font></span><span style="mso-spacerun:'yes';font-family:'Times New Roman';mso-fareast-font-family:SimHei;
font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimHei" >增压电磁阀振动后常温复试</font><font face="Times New Roman" >——</font><font face="SimHei" >导通与电阻测量数据</font></span><span style="mso-spacerun:'yes';font-family:'Times New Roman';mso-fareast-font-family:SimHei;
font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p><div align=center ><table class=MsoNormalTable  border=1  cellspacing=0  style="border-collapse:collapse;width:99.9600%;border:none;
mso-border-left-alt:1.0000pt solid windowtext;mso-border-top-alt:1.0000pt solid windowtext;mso-border-right-alt:1.0000pt solid windowtext;
mso-border-bottom-alt:1.0000pt solid windowtext;mso-border-insideh:0.5000pt solid windowtext;mso-border-insidev:0.5000pt solid windowtext;
mso-padding-alt:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;" ><tr style="height:15.7000pt;" ><td width=9.1000%  valign=center  rowspan=2  style="width:9.1000%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:1.0000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:1.0000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=237  align=center  style="text-align:center;" ><span style="font-family:SimSun;mso-ascii-font-family:'Times New Roman';mso-hansi-font-family:'Times New Roman';
mso-bidi-font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >序号</font></span><span style="font-family:SimSun;mso-ascii-font-family:'Times New Roman';mso-hansi-font-family:'Times New Roman';
mso-bidi-font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=9.1000%  valign=center  rowspan=2  style="width:9.1000%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:1.0000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=237  align=center  style="text-align:center;" ><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >试件</font></span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p><p class=237  align=center  style="text-align:center;" ><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >编号</font></span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=59.1200%  valign=center  colspan=7  style="width:59.1200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:1.0000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=237  align=center  style="text-align:center;" ><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >电阻值</font>/&#937;<font face="SimSun" >（环境温度：</font></span><span style="font-family:SimSun;mso-ascii-font-family:'Times New Roman';mso-hansi-font-family:'Times New Roman';
mso-bidi-font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >22.8</font></span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >℃</font><font face="SimSun" >）</font></span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=22.6200%  valign=center  rowspan=2  style="width:22.6200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:1.0000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:1.0000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=237  align=center  style="text-align:center;" ><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >换算后电阻值</font>/&#937;</span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p><p class=237  align=center  style="text-align:center;" ><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >（环境温度：</font>20℃<font face="SimSun" >）</font></span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td></tr><tr style="height:15.7000pt;" ><td width=8.2200%  valign=center  style="width:8.2200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=237  align=center  style="text-align:center;" ><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" >1<font face="SimSun" >和</font><font face="Times New Roman" >2</font></span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=8.2400%  valign=center  style="width:8.2400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=237  align=center  style="text-align:center;" ><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" >3<font face="SimSun" >和</font><font face="Times New Roman" >4</font></span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=237  align=center  style="text-align:center;" ><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" >1<font face="SimSun" >和</font><font face="Times New Roman" >3</font></span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=237  align=center  style="text-align:center;" ><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" >1<font face="SimSun" >和</font><font face="Times New Roman" >4</font></span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=237  align=center  style="text-align:center;" ><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" >2<font face="SimSun" >和</font><font face="Times New Roman" >3</font></span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=237  align=center  style="text-align:center;" ><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" >2<font face="SimSun" >和</font><font face="Times New Roman" >4</font></span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=8.8400%  valign=center  style="width:8.8400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=237  align=center  style="text-align:center;" ><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >平均值</font></span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td></tr><tr style="height:11.6000pt;" ><td width=134  valign=center  style="width:67.1000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:1.0000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="margin-left:21.0000pt;mso-para-margin-left:0.0000gd;text-indent:-21.0000pt;
mso-char-indent-count:0.0000;mso-pagination:widow-orphan;text-align:center;
vertical-align:middle;mso-list:l1 level1 lfo26;" ><![if !supportLists]><span style="font-family:SimSun;mso-ascii-font-family:'Times New Roman';mso-hansi-font-family:'Times New Roman';
mso-bidi-font-family:'Times New Roman';font-style:normal;font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><span style='mso-list:Ignore;' >1<span>&nbsp;</span></span></span><![endif]><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=9.1000%  valign=center  style="width:9.1000%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >8424</span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;font-size:10.5000pt;
mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=8.2200%  valign=center  style="width:8.2200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=8.2400%  valign=center  style="width:8.2400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.85 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.92 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.72 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.69 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.8400%  valign=center  style="width:8.8400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.80 </span><span style="font-family:'Times New Roman';color:rgb(0,0,0);font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=22.6200%  valign=center  style="width:22.6200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:1.0000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.51 </span><span style="font-family:'Times New Roman';color:rgb(0,0,0);font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td></tr><tr style="height:11.6000pt;" ><td width=134  valign=center  style="width:67.1000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:1.0000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="margin-left:21.0000pt;mso-para-margin-left:0.0000gd;text-indent:-21.0000pt;
mso-char-indent-count:0.0000;mso-pagination:widow-orphan;text-align:center;
vertical-align:middle;mso-list:l1 level1 lfo26;" ><![if !supportLists]><span style="font-family:SimSun;mso-ascii-font-family:'Times New Roman';mso-hansi-font-family:'Times New Roman';
mso-bidi-font-family:'Times New Roman';font-style:normal;font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><span style='mso-list:Ignore;' >2<span>&nbsp;</span></span></span><![endif]><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=9.1000%  valign=center  style="width:9.1000%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >15224</span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;font-size:10.5000pt;
mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=8.2200%  valign=center  style="width:8.2200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=8.2400%  valign=center  style="width:8.2400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.84 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.90 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.82 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.83 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.8400%  valign=center  style="width:8.8400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.85 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=22.6200%  valign=center  style="width:22.6200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:1.0000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.57 </span><span style="font-family:'Times New Roman';color:rgb(0,0,0);font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td></tr><tr style="height:11.6000pt;" ><td width=134  valign=center  style="width:67.1000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:1.0000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="margin-left:21.0000pt;mso-para-margin-left:0.0000gd;text-indent:-21.0000pt;
mso-char-indent-count:0.0000;mso-pagination:widow-orphan;text-align:center;
vertical-align:middle;mso-list:l1 level1 lfo26;" ><![if !supportLists]><span style="font-family:SimSun;mso-ascii-font-family:'Times New Roman';mso-hansi-font-family:'Times New Roman';
mso-bidi-font-family:'Times New Roman';font-style:normal;font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><span style='mso-list:Ignore;' >3<span>&nbsp;</span></span></span><![endif]><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=9.1000%  valign=center  style="width:9.1000%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >20024</span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;font-size:10.5000pt;
mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=8.2200%  valign=center  style="width:8.2200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=8.2400%  valign=center  style="width:8.2400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.97 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.95 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.76 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.75 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.8400%  valign=center  style="width:8.8400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.86 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=22.6200%  valign=center  style="width:22.6200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:1.0000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.58 </span><span style="font-family:'Times New Roman';color:rgb(0,0,0);font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td></tr><tr style="height:11.6000pt;" ><td width=134  valign=center  style="width:67.1000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:1.0000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="margin-left:21.0000pt;mso-para-margin-left:0.0000gd;text-indent:-21.0000pt;
mso-char-indent-count:0.0000;mso-pagination:widow-orphan;text-align:center;
vertical-align:middle;mso-list:l1 level1 lfo26;" ><![if !supportLists]><span style="font-family:SimSun;mso-ascii-font-family:'Times New Roman';mso-hansi-font-family:'Times New Roman';
mso-bidi-font-family:'Times New Roman';font-style:normal;font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><span style='mso-list:Ignore;' >4<span>&nbsp;</span></span></span><![endif]><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=9.1000%  valign=center  style="width:9.1000%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >22024</span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;font-size:10.5000pt;
mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=8.2200%  valign=center  style="width:8.2200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=8.2400%  valign=center  style="width:8.2400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.74 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.73 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.68 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.66 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.8400%  valign=center  style="width:8.8400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.70 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=22.6200%  valign=center  style="width:22.6200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:1.0000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.42 </span><span style="font-family:'Times New Roman';color:rgb(0,0,0);font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td></tr><tr style="height:11.6000pt;" ><td width=134  valign=center  style="width:67.1000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:1.0000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="margin-left:21.0000pt;mso-para-margin-left:0.0000gd;text-indent:-21.0000pt;
mso-char-indent-count:0.0000;mso-pagination:widow-orphan;text-align:center;
vertical-align:middle;mso-list:l1 level1 lfo26;" ><![if !supportLists]><span style="font-family:SimSun;mso-ascii-font-family:'Times New Roman';mso-hansi-font-family:'Times New Roman';
mso-bidi-font-family:'Times New Roman';font-style:normal;font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><span style='mso-list:Ignore;' >5<span>&nbsp;</span></span></span><![endif]><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=9.1000%  valign=center  style="width:9.1000%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >22124</span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;font-size:10.5000pt;
mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=8.2200%  valign=center  style="width:8.2200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=8.2400%  valign=center  style="width:8.2400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.85 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.86 </span><span style="font-family:'Times New Roman';color:rgb(0,0,0);font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.74 </span><span style="font-family:'Times New Roman';color:rgb(0,0,0);font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.73 </span><span style="font-family:'Times New Roman';color:rgb(0,0,0);font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.8400%  valign=center  style="width:8.8400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.80 </span><span style="font-family:'Times New Roman';color:rgb(0,0,0);font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=22.6200%  valign=center  style="width:22.6200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:1.0000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.51 </span><span style="font-family:'Times New Roman';color:rgb(0,0,0);font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td></tr><tr style="height:11.6000pt;" ><td width=134  valign=center  style="width:67.1000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:1.0000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="margin-left:21.0000pt;mso-para-margin-left:0.0000gd;text-indent:-21.0000pt;
mso-char-indent-count:0.0000;mso-pagination:widow-orphan;text-align:center;
vertical-align:middle;mso-list:l1 level1 lfo26;" ><![if !supportLists]><span style="font-family:SimSun;mso-ascii-font-family:'Times New Roman';mso-hansi-font-family:'Times New Roman';
mso-bidi-font-family:'Times New Roman';font-style:normal;font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><span style='mso-list:Ignore;' >6<span>&nbsp;</span></span></span><![endif]><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=9.1000%  valign=center  style="width:9.1000%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >22323</span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.2200%  valign=center  style="width:8.2200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=8.2400%  valign=center  style="width:8.2400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.29 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.28 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.22 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.24 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.8400%  valign=center  style="width:8.8400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.26 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=22.6200%  valign=center  style="width:22.6200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:1.0000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >24.98 </span><span style="font-family:'Times New Roman';color:rgb(0,0,0);font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td></tr><tr style="height:11.6000pt;" ><td width=134  valign=center  style="width:67.1000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:1.0000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="margin-left:21.0000pt;mso-para-margin-left:0.0000gd;text-indent:-21.0000pt;
mso-char-indent-count:0.0000;mso-pagination:widow-orphan;text-align:center;
vertical-align:middle;mso-list:l1 level1 lfo26;" ><![if !supportLists]><span style="font-family:SimSun;mso-ascii-font-family:'Times New Roman';mso-hansi-font-family:'Times New Roman';
mso-bidi-font-family:'Times New Roman';font-style:normal;font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><span style='mso-list:Ignore;' >7<span>&nbsp;</span></span></span><![endif]><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=9.1000%  valign=center  style="width:9.1000%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >23124</span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.2200%  valign=center  style="width:8.2200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=8.2400%  valign=center  style="width:8.2400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >26.12 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >26.08 </span><span style="font-family:'Times New Roman';color:rgb(0,0,0);font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >26.02 </span><span style="font-family:'Times New Roman';color:rgb(0,0,0);font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >26.01 </span><span style="font-family:'Times New Roman';color:rgb(0,0,0);font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.8400%  valign=center  style="width:8.8400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >26.06 </span><span style="font-family:'Times New Roman';color:rgb(0,0,0);font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=22.6200%  valign=center  style="width:22.6200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:1.0000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.77 </span><span style="font-family:'Times New Roman';color:rgb(0,0,0);font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td></tr><tr style="height:11.6000pt;" ><td width=134  valign=center  style="width:67.1000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:1.0000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="margin-left:21.0000pt;mso-para-margin-left:0.0000gd;text-indent:-21.0000pt;
mso-char-indent-count:0.0000;mso-pagination:widow-orphan;text-align:center;
vertical-align:middle;mso-list:l1 level1 lfo26;" ><![if !supportLists]><span style="font-family:SimSun;mso-ascii-font-family:'Times New Roman';mso-hansi-font-family:'Times New Roman';
mso-bidi-font-family:'Times New Roman';font-style:normal;font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><span style='mso-list:Ignore;' >8<span>&nbsp;</span></span></span><![endif]><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=9.1000%  valign=center  style="width:9.1000%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >24324</span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.2200%  valign=center  style="width:8.2200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.2400%  valign=center  style="width:8.2400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.89 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.89 </span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.84 </span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.84 </span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.8400%  valign=center  style="width:8.8400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.87 </span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=22.6200%  valign=center  style="width:22.6200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:1.0000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.58 </span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td></tr><tr style="height:11.6000pt;" ><td width=134  valign=center  style="width:67.1000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:1.0000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="margin-left:21.0000pt;mso-para-margin-left:0.0000gd;text-indent:-21.0000pt;
mso-char-indent-count:0.0000;mso-pagination:widow-orphan;text-align:center;
vertical-align:middle;mso-list:l1 level1 lfo26;" ><![if !supportLists]><span style="font-family:SimSun;mso-ascii-font-family:'Times New Roman';mso-hansi-font-family:'Times New Roman';
mso-bidi-font-family:'Times New Roman';font-style:normal;font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><span style='mso-list:Ignore;' >9<span>&nbsp;</span></span></span><![endif]><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=9.1000%  valign=center  style="width:9.1000%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >24724</span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.2200%  valign=center  style="width:8.2200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.2400%  valign=center  style="width:8.2400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.98 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.96 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.70 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.71 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.8400%  valign=center  style="width:8.8400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.84 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=22.6200%  valign=center  style="width:22.6200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:1.0000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.56 </span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td></tr><tr style="height:11.6000pt;" ><td width=134  valign=center  style="width:67.1000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:1.0000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="margin-left:21.0000pt;mso-para-margin-left:0.0000gd;text-indent:-21.0000pt;
mso-char-indent-count:0.0000;mso-pagination:widow-orphan;text-align:center;
vertical-align:middle;mso-list:l1 level1 lfo26;" ><![if !supportLists]><span style="font-family:SimSun;mso-ascii-font-family:'Times New Roman';mso-hansi-font-family:'Times New Roman';
mso-bidi-font-family:'Times New Roman';font-style:normal;font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><span style='mso-list:Ignore;' >10<span>&nbsp;</span></span></span><![endif]><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=9.1000%  valign=center  style="width:9.1000%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >24824</span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.2200%  valign=center  style="width:8.2200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.2400%  valign=center  style="width:8.2400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.98 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.96 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >26.02 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >26.07 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.8400%  valign=center  style="width:8.8400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >26.01 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=22.6200%  valign=center  style="width:22.6200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:1.0000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.72 </span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td></tr><tr style="height:11.6000pt;" ><td width=134  valign=center  style="width:67.1000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:1.0000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="margin-left:21.0000pt;mso-para-margin-left:0.0000gd;text-indent:-21.0000pt;
mso-char-indent-count:0.0000;mso-pagination:widow-orphan;text-align:center;
vertical-align:middle;mso-list:l1 level1 lfo26;" ><![if !supportLists]><span style="font-family:SimSun;mso-ascii-font-family:'Times New Roman';mso-hansi-font-family:'Times New Roman';
mso-bidi-font-family:'Times New Roman';font-style:normal;font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><span style='mso-list:Ignore;' >11<span>&nbsp;</span></span></span><![endif]><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=9.1000%  valign=center  style="width:9.1000%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >24923</span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.2200%  valign=center  style="width:8.2200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.2400%  valign=center  style="width:8.2400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.73 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.78 </span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.82 </span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.84 </span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.8400%  valign=center  style="width:8.8400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.79 </span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=22.6200%  valign=center  style="width:22.6200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:1.0000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.51 </span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td></tr><tr style="height:11.6000pt;" ><td width=134  valign=center  style="width:67.1000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:1.0000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="margin-left:21.0000pt;mso-para-margin-left:0.0000gd;text-indent:-21.0000pt;
mso-char-indent-count:0.0000;mso-pagination:widow-orphan;text-align:center;
vertical-align:middle;mso-list:l1 level1 lfo26;" ><![if !supportLists]><span style="font-family:SimSun;mso-ascii-font-family:'Times New Roman';mso-hansi-font-family:'Times New Roman';
mso-bidi-font-family:'Times New Roman';font-style:normal;font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><span style='mso-list:Ignore;' >12<span>&nbsp;</span></span></span><![endif]><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=9.1000%  valign=center  style="width:9.1000%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25024</span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.2200%  valign=center  style="width:8.2200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.2400%  valign=center  style="width:8.2400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.83 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.79 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.77 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.72 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.8400%  valign=center  style="width:8.8400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.78 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=22.6200%  valign=center  style="width:22.6200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:1.0000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.50 </span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td></tr><tr style="height:11.6000pt;" ><td width=134  valign=center  style="width:67.1000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:1.0000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="margin-left:21.0000pt;mso-para-margin-left:0.0000gd;text-indent:-21.0000pt;
mso-char-indent-count:0.0000;mso-pagination:widow-orphan;text-align:center;
vertical-align:middle;mso-list:l1 level1 lfo26;" ><![if !supportLists]><span style="font-family:SimSun;mso-ascii-font-family:'Times New Roman';mso-hansi-font-family:'Times New Roman';
mso-bidi-font-family:'Times New Roman';font-style:normal;font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><span style='mso-list:Ignore;' >13<span>&nbsp;</span></span></span><![endif]><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=9.1000%  valign=center  style="width:9.1000%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25624</span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.2200%  valign=center  style="width:8.2200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.2400%  valign=center  style="width:8.2400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.86 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.87 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.92 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.88 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.8400%  valign=center  style="width:8.8400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.88 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=22.6200%  valign=center  style="width:22.6200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:1.0000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.60 </span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td></tr><tr style="height:11.6000pt;" ><td width=134  valign=center  style="width:67.1000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:1.0000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="margin-left:21.0000pt;mso-para-margin-left:0.0000gd;text-indent:-21.0000pt;
mso-char-indent-count:0.0000;mso-pagination:widow-orphan;text-align:center;
vertical-align:middle;mso-list:l1 level1 lfo26;" ><![if !supportLists]><span style="font-family:SimSun;mso-ascii-font-family:'Times New Roman';mso-hansi-font-family:'Times New Roman';
mso-bidi-font-family:'Times New Roman';font-style:normal;font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><span style='mso-list:Ignore;' >14<span>&nbsp;</span></span></span><![endif]><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=9.1000%  valign=center  style="width:9.1000%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >26223</span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.2200%  valign=center  style="width:8.2200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.2400%  valign=center  style="width:8.2400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.68 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.75 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.35 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.35 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.8400%  valign=center  style="width:8.8400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.53 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=22.6200%  valign=center  style="width:22.6200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:1.0000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.25 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td></tr><tr style="height:11.6000pt;" ><td width=134  valign=center  style="width:67.1000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:1.0000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="margin-left:21.0000pt;mso-para-margin-left:0.0000gd;text-indent:-21.0000pt;
mso-char-indent-count:0.0000;mso-pagination:widow-orphan;text-align:center;
vertical-align:middle;mso-list:l1 level1 lfo26;" ><![if !supportLists]><span style="font-family:SimSun;mso-ascii-font-family:'Times New Roman';mso-hansi-font-family:'Times New Roman';
mso-bidi-font-family:'Times New Roman';font-style:normal;font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><span style='mso-list:Ignore;' >15<span>&nbsp;</span></span></span><![endif]><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=9.1000%  valign=center  style="width:9.1000%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >26323</span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.2200%  valign=center  style="width:8.2200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.2400%  valign=center  style="width:8.2400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.83 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.86 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.81 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.79 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.8400%  valign=center  style="width:8.8400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.82 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=22.6200%  valign=center  style="width:22.6200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:1.0000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.54 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td></tr><tr style="height:11.6000pt;" ><td width=134  valign=center  style="width:67.1000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:1.0000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="margin-left:21.0000pt;mso-para-margin-left:0.0000gd;text-indent:-21.0000pt;
mso-char-indent-count:0.0000;mso-pagination:widow-orphan;text-align:center;
vertical-align:middle;mso-list:l1 level1 lfo26;" ><![if !supportLists]><span style="font-family:SimSun;mso-ascii-font-family:'Times New Roman';mso-hansi-font-family:'Times New Roman';
mso-bidi-font-family:'Times New Roman';font-style:normal;font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><span style='mso-list:Ignore;' >16<span>&nbsp;</span></span></span><![endif]><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=9.1000%  valign=center  style="width:9.1000%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >27123</span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.2200%  valign=center  style="width:8.2200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.2400%  valign=center  style="width:8.2400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >26.11 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >26.15 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >26.08 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >26.02 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.8400%  valign=center  style="width:8.8400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >26.09 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=22.6200%  valign=center  style="width:22.6200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:1.0000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.81 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td></tr><tr style="height:11.6000pt;" ><td width=134  valign=center  style="width:67.1000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:1.0000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="margin-left:21.0000pt;mso-para-margin-left:0.0000gd;text-indent:-21.0000pt;
mso-char-indent-count:0.0000;mso-pagination:widow-orphan;text-align:center;
vertical-align:middle;mso-list:l1 level1 lfo26;" ><![if !supportLists]><span style="font-family:SimSun;mso-ascii-font-family:'Times New Roman';mso-hansi-font-family:'Times New Roman';
mso-bidi-font-family:'Times New Roman';font-style:normal;font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><span style='mso-list:Ignore;' >17<span>&nbsp;</span></span></span><![endif]><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=9.1000%  valign=center  style="width:9.1000%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >27824</span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.2200%  valign=center  style="width:8.2200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.2400%  valign=center  style="width:8.2400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.78 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.76 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.84 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.73 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.8400%  valign=center  style="width:8.8400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.78 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=22.6200%  valign=center  style="width:22.6200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:1.0000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.50 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td></tr><tr style="height:11.6000pt;" ><td width=134  valign=top  style="width:67.1000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:1.0000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="margin-left:21.0000pt;mso-para-margin-left:0.0000gd;text-indent:-21.0000pt;
mso-char-indent-count:0.0000;mso-pagination:widow-orphan;text-align:center;
vertical-align:middle;mso-list:l1 level1 lfo26;" ><![if !supportLists]><span style="font-family:SimSun;mso-ascii-font-family:'Times New Roman';mso-hansi-font-family:'Times New Roman';
mso-bidi-font-family:'Times New Roman';font-style:normal;font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><span style='mso-list:Ignore;' >18<span>&nbsp;</span></span></span><![endif]><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=9.1000%  valign=center  style="width:9.1000%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >32523</span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.2200%  valign=center  style="width:8.2200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.2400%  valign=center  style="width:8.2400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.71 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.70 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.68 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.70 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.8400%  valign=center  style="width:8.8400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.70 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=22.6200%  valign=center  style="width:22.6200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:1.0000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.42 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td></tr><tr style="height:11.6000pt;" ><td width=134  valign=top  style="width:67.1000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:1.0000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="margin-left:21.0000pt;mso-para-margin-left:0.0000gd;text-indent:-21.0000pt;
mso-char-indent-count:0.0000;mso-pagination:widow-orphan;text-align:center;
vertical-align:middle;mso-list:l1 level1 lfo26;" ><![if !supportLists]><span style="font-family:SimSun;mso-ascii-font-family:'Times New Roman';mso-hansi-font-family:'Times New Roman';
mso-bidi-font-family:'Times New Roman';font-style:normal;font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><span style='mso-list:Ignore;' >19<span>&nbsp;</span></span></span><![endif]><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=9.1000%  valign=center  style="width:9.1000%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >32923</span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.2200%  valign=center  style="width:8.2200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.2400%  valign=center  style="width:8.2400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.81 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.81 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.81 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.81 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.8400%  valign=center  style="width:8.8400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.81 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=22.6200%  valign=center  style="width:22.6200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:1.0000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.53 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td></tr><tr style="height:11.6000pt;" ><td width=134  valign=top  style="width:67.1000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:1.0000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="margin-left:21.0000pt;mso-para-margin-left:0.0000gd;text-indent:-21.0000pt;
mso-char-indent-count:0.0000;mso-pagination:widow-orphan;text-align:center;
vertical-align:middle;mso-list:l1 level1 lfo26;" ><![if !supportLists]><span style="font-family:SimSun;mso-ascii-font-family:'Times New Roman';mso-hansi-font-family:'Times New Roman';
mso-bidi-font-family:'Times New Roman';font-style:normal;font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><span style='mso-list:Ignore;' >20<span>&nbsp;</span></span></span><![endif]><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=9.1000%  valign=center  style="width:9.1000%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >33524</span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.2200%  valign=center  style="width:8.2200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.2400%  valign=center  style="width:8.2400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.69 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.67 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.71 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.71 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.8400%  valign=center  style="width:8.8400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.70 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=22.6200%  valign=center  style="width:22.6200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:1.0000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.42 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td></tr><tr style="height:11.6000pt;" ><td width=134  valign=top  style="width:67.1000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:1.0000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="margin-left:21.0000pt;mso-para-margin-left:0.0000gd;text-indent:-21.0000pt;
mso-char-indent-count:0.0000;mso-pagination:widow-orphan;text-align:center;
vertical-align:middle;mso-list:l1 level1 lfo26;" ><![if !supportLists]><span style="font-family:SimSun;mso-ascii-font-family:'Times New Roman';mso-hansi-font-family:'Times New Roman';
mso-bidi-font-family:'Times New Roman';font-style:normal;font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><span style='mso-list:Ignore;' >21<span>&nbsp;</span></span></span><![endif]><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=9.1000%  valign=center  style="width:9.1000%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >33824</span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.2200%  valign=center  style="width:8.2200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.2400%  valign=center  style="width:8.2400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.94 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.98 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.96 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.96 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.8400%  valign=center  style="width:8.8400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.96 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=22.6200%  valign=center  style="width:22.6200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:1.0000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.68 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td></tr><tr style="height:11.6000pt;" ><td width=134  valign=top  style="width:67.1000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:1.0000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="margin-left:21.0000pt;mso-para-margin-left:0.0000gd;text-indent:-21.0000pt;
mso-char-indent-count:0.0000;mso-pagination:widow-orphan;text-align:center;
vertical-align:middle;mso-list:l1 level1 lfo26;" ><![if !supportLists]><span style="font-family:SimSun;mso-ascii-font-family:'Times New Roman';mso-hansi-font-family:'Times New Roman';
mso-bidi-font-family:'Times New Roman';font-style:normal;font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><span style='mso-list:Ignore;' >22<span>&nbsp;</span></span></span><![endif]><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=9.1000%  valign=center  style="width:9.1000%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >33923</span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.2200%  valign=center  style="width:8.2200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.2400%  valign=center  style="width:8.2400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.99 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.96 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.94 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.86 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.8400%  valign=center  style="width:8.8400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.94 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=22.6200%  valign=center  style="width:22.6200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:1.0000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.66 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td></tr><tr style="height:11.6000pt;" ><td width=134  valign=top  style="width:67.1000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:1.0000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="margin-left:21.0000pt;mso-para-margin-left:0.0000gd;text-indent:-21.0000pt;
mso-char-indent-count:0.0000;mso-pagination:widow-orphan;text-align:center;
vertical-align:middle;mso-list:l1 level1 lfo26;" ><![if !supportLists]><span style="font-family:SimSun;mso-ascii-font-family:'Times New Roman';mso-hansi-font-family:'Times New Roman';
mso-bidi-font-family:'Times New Roman';font-style:normal;font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><span style='mso-list:Ignore;' >23<span>&nbsp;</span></span></span><![endif]><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=9.1000%  valign=center  style="width:9.1000%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >34124</span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.2200%  valign=center  style="width:8.2200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.2400%  valign=center  style="width:8.2400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.83 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.86 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.63 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.62 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.8400%  valign=center  style="width:8.8400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.74 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=22.6200%  valign=center  style="width:22.6200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:1.0000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.45 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td></tr><tr style="height:11.6000pt;" ><td width=134  valign=top  style="width:67.1000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:1.0000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="margin-left:21.0000pt;mso-para-margin-left:0.0000gd;text-indent:-21.0000pt;
mso-char-indent-count:0.0000;mso-pagination:widow-orphan;text-align:center;
vertical-align:middle;mso-list:l1 level1 lfo26;" ><![if !supportLists]><span style="font-family:SimSun;mso-ascii-font-family:'Times New Roman';mso-hansi-font-family:'Times New Roman';
mso-bidi-font-family:'Times New Roman';font-style:normal;font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><span style='mso-list:Ignore;' >24<span>&nbsp;</span></span></span><![endif]><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=9.1000%  valign=center  style="width:9.1000%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >34223</span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.2200%  valign=center  style="width:8.2200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.2400%  valign=center  style="width:8.2400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.94 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.94 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.83 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.82 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.8400%  valign=center  style="width:8.8400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.88 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=22.6200%  valign=center  style="width:22.6200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:1.0000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.60 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td></tr><tr style="height:11.6000pt;" ><td width=134  valign=top  style="width:67.1000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:1.0000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="margin-left:21.0000pt;mso-para-margin-left:0.0000gd;text-indent:-21.0000pt;
mso-char-indent-count:0.0000;mso-pagination:widow-orphan;text-align:center;
vertical-align:middle;mso-list:l1 level1 lfo26;" ><![if !supportLists]><span style="font-family:SimSun;mso-ascii-font-family:'Times New Roman';mso-hansi-font-family:'Times New Roman';
mso-bidi-font-family:'Times New Roman';font-style:normal;font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><span style='mso-list:Ignore;' >25<span>&nbsp;</span></span></span><![endif]><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=9.1000%  valign=center  style="width:9.1000%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >34524</span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.2200%  valign=center  style="width:8.2200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.2400%  valign=center  style="width:8.2400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.87 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.87 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.87 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.87 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.8400%  valign=center  style="width:8.8400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.87 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=22.6200%  valign=center  style="width:22.6200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:1.0000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.59 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td></tr><tr style="height:11.6000pt;" ><td width=134  valign=top  style="width:67.1000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:1.0000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="margin-left:21.0000pt;mso-para-margin-left:0.0000gd;text-indent:-21.0000pt;
mso-char-indent-count:0.0000;mso-pagination:widow-orphan;text-align:center;
vertical-align:middle;mso-list:l1 level1 lfo26;" ><![if !supportLists]><span style="font-family:SimSun;mso-ascii-font-family:'Times New Roman';mso-hansi-font-family:'Times New Roman';
mso-bidi-font-family:'Times New Roman';font-style:normal;font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><span style='mso-list:Ignore;' >26<span>&nbsp;</span></span></span><![endif]><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=9.1000%  valign=center  style="width:9.1000%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >35124</span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.2200%  valign=center  style="width:8.2200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.2400%  valign=center  style="width:8.2400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.88 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.88 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.88 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.88 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.8400%  valign=center  style="width:8.8400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.88 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=22.6200%  valign=center  style="width:22.6200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:1.0000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.60 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td></tr><tr style="height:11.6000pt;" ><td width=134  valign=top  style="width:67.1000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:1.0000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="margin-left:21.0000pt;mso-para-margin-left:0.0000gd;text-indent:-21.0000pt;
mso-char-indent-count:0.0000;mso-pagination:widow-orphan;text-align:center;
vertical-align:middle;mso-list:l1 level1 lfo26;" ><![if !supportLists]><span style="font-family:SimSun;mso-ascii-font-family:'Times New Roman';mso-hansi-font-family:'Times New Roman';
mso-bidi-font-family:'Times New Roman';font-style:normal;font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><span style='mso-list:Ignore;' >27<span>&nbsp;</span></span></span><![endif]><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=9.1000%  valign=center  style="width:9.1000%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >35824</span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.2200%  valign=center  style="width:8.2200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.2400%  valign=center  style="width:8.2400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.88 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.90 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.87 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.92 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.8400%  valign=center  style="width:8.8400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.89 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=22.6200%  valign=center  style="width:22.6200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:1.0000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.61 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td></tr><tr style="height:11.6000pt;" ><td width=134  valign=top  style="width:67.1000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:1.0000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="margin-left:21.0000pt;mso-para-margin-left:0.0000gd;text-indent:-21.0000pt;
mso-char-indent-count:0.0000;mso-pagination:widow-orphan;text-align:center;
vertical-align:middle;mso-list:l1 level1 lfo26;" ><![if !supportLists]><span style="font-family:SimSun;mso-ascii-font-family:'Times New Roman';mso-hansi-font-family:'Times New Roman';
mso-bidi-font-family:'Times New Roman';font-style:normal;font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><span style='mso-list:Ignore;' >28<span>&nbsp;</span></span></span><![endif]><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=9.1000%  valign=center  style="width:9.1000%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >36024</span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.2200%  valign=center  style="width:8.2200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.2400%  valign=center  style="width:8.2400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.73 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.78 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.72 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.77 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.8400%  valign=center  style="width:8.8400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.75 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=22.6200%  valign=center  style="width:22.6200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:1.0000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.47 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td></tr><tr style="height:11.6000pt;" ><td width=134  valign=top  style="width:67.1000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:1.0000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="margin-left:21.0000pt;mso-para-margin-left:0.0000gd;text-indent:-21.0000pt;
mso-char-indent-count:0.0000;mso-pagination:widow-orphan;text-align:center;
vertical-align:middle;mso-list:l1 level1 lfo26;" ><![if !supportLists]><span style="font-family:SimSun;mso-ascii-font-family:'Times New Roman';mso-hansi-font-family:'Times New Roman';
mso-bidi-font-family:'Times New Roman';font-style:normal;font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><span style='mso-list:Ignore;' >29<span>&nbsp;</span></span></span><![endif]><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=9.1000%  valign=center  style="width:9.1000%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >36123</span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.2200%  valign=center  style="width:8.2200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.2400%  valign=center  style="width:8.2400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.96 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.92 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.80 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.81 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.8400%  valign=center  style="width:8.8400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.87 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=22.6200%  valign=center  style="width:22.6200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:1.0000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.59 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td></tr><tr style="height:11.6000pt;" ><td width=134  valign=top  style="width:67.1000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:1.0000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="margin-left:21.0000pt;mso-para-margin-left:0.0000gd;text-indent:-21.0000pt;
mso-char-indent-count:0.0000;mso-pagination:widow-orphan;text-align:center;
vertical-align:middle;mso-list:l1 level1 lfo26;" ><![if !supportLists]><span style="font-family:SimSun;mso-ascii-font-family:'Times New Roman';mso-hansi-font-family:'Times New Roman';
mso-bidi-font-family:'Times New Roman';font-style:normal;font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><span style='mso-list:Ignore;' >30<span>&nbsp;</span></span></span><![endif]><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=9.1000%  valign=center  style="width:9.1000%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >36124</span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.2200%  valign=center  style="width:8.2200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.2400%  valign=center  style="width:8.2400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.84 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.83 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.81 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.83 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.8400%  valign=center  style="width:8.8400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.83 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=22.6200%  valign=center  style="width:22.6200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:1.0000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.55 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td></tr><tr style="height:11.6000pt;" ><td width=134  valign=top  style="width:67.1000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:1.0000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="margin-left:21.0000pt;mso-para-margin-left:0.0000gd;text-indent:-21.0000pt;
mso-char-indent-count:0.0000;mso-pagination:widow-orphan;text-align:center;
vertical-align:middle;mso-list:l1 level1 lfo26;" ><![if !supportLists]><span style="font-family:SimSun;mso-ascii-font-family:'Times New Roman';mso-hansi-font-family:'Times New Roman';
mso-bidi-font-family:'Times New Roman';font-style:normal;font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><span style='mso-list:Ignore;' >31<span>&nbsp;</span></span></span><![endif]><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=9.1000%  valign=center  style="width:9.1000%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >36223</span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.2200%  valign=center  style="width:8.2200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.2400%  valign=center  style="width:8.2400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.74 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.70 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.72 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.74 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.8400%  valign=center  style="width:8.8400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.73 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=22.6200%  valign=center  style="width:22.6200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:1.0000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.45 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td></tr><tr style="height:11.6000pt;" ><td width=134  valign=top  style="width:67.1000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:1.0000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="margin-left:21.0000pt;mso-para-margin-left:0.0000gd;text-indent:-21.0000pt;
mso-char-indent-count:0.0000;mso-pagination:widow-orphan;text-align:center;
vertical-align:middle;mso-list:l1 level1 lfo26;" ><![if !supportLists]><span style="font-family:SimSun;mso-ascii-font-family:'Times New Roman';mso-hansi-font-family:'Times New Roman';
mso-bidi-font-family:'Times New Roman';font-style:normal;font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><span style='mso-list:Ignore;' >32<span>&nbsp;</span></span></span><![endif]><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=9.1000%  valign=center  style="width:9.1000%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >37323</span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.2200%  valign=center  style="width:8.2200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.2400%  valign=center  style="width:8.2400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.67 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.62 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.55 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.52 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.8400%  valign=center  style="width:8.8400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.59 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=22.6200%  valign=center  style="width:22.6200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:1.0000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.31 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td></tr><tr style="height:11.6000pt;" ><td width=134  valign=top  style="width:67.1000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:1.0000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="margin-left:21.0000pt;mso-para-margin-left:0.0000gd;text-indent:-21.0000pt;
mso-char-indent-count:0.0000;mso-pagination:widow-orphan;text-align:center;
vertical-align:middle;mso-list:l1 level1 lfo26;" ><![if !supportLists]><span style="font-family:SimSun;mso-ascii-font-family:'Times New Roman';mso-hansi-font-family:'Times New Roman';
mso-bidi-font-family:'Times New Roman';font-style:normal;font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><span style='mso-list:Ignore;' >33<span>&nbsp;</span></span></span><![endif]><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=9.1000%  valign=center  style="width:9.1000%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >37424</span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.2200%  valign=center  style="width:8.2200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.2400%  valign=center  style="width:8.2400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.87 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.84 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.66 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.62 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.8400%  valign=center  style="width:8.8400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.75 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=22.6200%  valign=center  style="width:22.6200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:1.0000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.47 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td></tr><tr style="height:11.6000pt;" ><td width=134  valign=top  style="width:67.1000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:1.0000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="margin-left:21.0000pt;mso-para-margin-left:0.0000gd;text-indent:-21.0000pt;
mso-char-indent-count:0.0000;mso-pagination:widow-orphan;text-align:center;
vertical-align:middle;mso-list:l1 level1 lfo26;" ><![if !supportLists]><span style="font-family:SimSun;mso-ascii-font-family:'Times New Roman';mso-hansi-font-family:'Times New Roman';
mso-bidi-font-family:'Times New Roman';font-style:normal;font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><span style='mso-list:Ignore;' >34<span>&nbsp;</span></span></span><![endif]><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=9.1000%  valign=center  style="width:9.1000%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >37524</span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.2200%  valign=center  style="width:8.2200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.2400%  valign=center  style="width:8.2400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.90 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.95 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.95 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.93 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.8400%  valign=center  style="width:8.8400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.93 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=22.6200%  valign=center  style="width:22.6200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:1.0000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.65 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td></tr><tr style="height:11.6000pt;" ><td width=134  valign=top  style="width:67.1000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:1.0000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="margin-left:21.0000pt;mso-para-margin-left:0.0000gd;text-indent:-21.0000pt;
mso-char-indent-count:0.0000;mso-pagination:widow-orphan;text-align:center;
vertical-align:middle;mso-list:l1 level1 lfo26;" ><![if !supportLists]><span style="font-family:SimSun;mso-ascii-font-family:'Times New Roman';mso-hansi-font-family:'Times New Roman';
mso-bidi-font-family:'Times New Roman';font-style:normal;font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><span style='mso-list:Ignore;' >35<span>&nbsp;</span></span></span><![endif]><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=9.1000%  valign=center  style="width:9.1000%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >37623</span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.2200%  valign=center  style="width:8.2200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.2400%  valign=center  style="width:8.2400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.81 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.87 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.83 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.84 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.8400%  valign=center  style="width:8.8400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.84 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=22.6200%  valign=center  style="width:22.6200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:1.0000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.56 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td></tr><tr style="height:11.6000pt;" ><td width=134  valign=top  style="width:67.1000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:1.0000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="margin-left:21.0000pt;mso-para-margin-left:0.0000gd;text-indent:-21.0000pt;
mso-char-indent-count:0.0000;mso-pagination:widow-orphan;text-align:center;
vertical-align:middle;mso-list:l1 level1 lfo26;" ><![if !supportLists]><span style="font-family:SimSun;mso-ascii-font-family:'Times New Roman';mso-hansi-font-family:'Times New Roman';
mso-bidi-font-family:'Times New Roman';font-style:normal;font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><span style='mso-list:Ignore;' >36<span>&nbsp;</span></span></span><![endif]><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=9.1000%  valign=center  style="width:9.1000%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >37624</span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.2200%  valign=center  style="width:8.2200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.2400%  valign=center  style="width:8.2400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.88 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.88 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.83 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.81 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.8400%  valign=center  style="width:8.8400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.85 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=22.6200%  valign=center  style="width:22.6200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:1.0000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.57 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td></tr><tr style="height:11.6000pt;" ><td width=134  valign=top  style="width:67.1000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:1.0000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:1.0000pt solid windowtext;" ><p class=MsoNormal  align=center  style="margin-left:21.0000pt;mso-para-margin-left:0.0000gd;text-indent:-21.0000pt;
mso-char-indent-count:0.0000;mso-pagination:widow-orphan;text-align:center;
vertical-align:middle;mso-list:l1 level1 lfo26;" ><![if !supportLists]><span style="font-family:SimSun;mso-ascii-font-family:'Times New Roman';mso-hansi-font-family:'Times New Roman';
mso-bidi-font-family:'Times New Roman';font-style:normal;font-size:10.5000pt;
mso-font-kerning:0.0000pt;" ><span style='mso-list:Ignore;' >37<span>&nbsp;</span></span></span><![endif]><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=9.1000%  valign=center  style="width:9.1000%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:1.0000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >37724</span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.2200%  valign=center  style="width:8.2200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:1.0000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.2400%  valign=center  style="width:8.2400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:1.0000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
mso-ansi-font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><font face="SimSun" >导通</font></span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:1.0000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.82 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:1.0000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.98 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:1.0000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.86 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.4400%  valign=center  style="width:8.4400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:1.0000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.93 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=8.8400%  valign=center  style="width:8.8400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:1.0000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.90 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=22.6200%  valign=center  style="width:22.6200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:1.0000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:1.0000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" >25.62 </span><span style="font-family:'Times New Roman';mso-fareast-font-family:SimSun;color:rgb(0,0,0);
font-style:normal;font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td></tr></table></div><p class=MsoNormal  style="line-height:150%;" ><span style="mso-spacerun:'yes';font-family:SimHei;font-size:10.5000pt;
mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></p><table class=MsoNormalTable  border=1  cellspacing=0  style="border-collapse:collapse;mso-table-layout-alt:fixed;border:none;
mso-border-left-alt:0.5000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;mso-border-insideh:0.5000pt solid windowtext;mso-border-insidev:0.5000pt solid windowtext;
mso-padding-alt:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;" ><tr><td width=138  valign=center  style="width:69.2500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=317  align=center  style="margin-left:42.3000pt;text-indent:-21.0000pt;mso-char-indent-count:0.0000;
text-align:center;mso-list:l16 level1 lfo27;" ><![if !supportLists]><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><span style='mso-list:Ignore;' >1<span>&nbsp;</span></span></span><![endif]><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=147  valign=center  style="width:73.7000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" >27824</span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:SimSun;font-size:11.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:SimSun;font-size:11.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >16.025</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=172  valign=center  style="width:86.2500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" >15.941</span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >23.937</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=150  valign=center  style="width:75.3000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >0.4</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=157  valign=center  style="width:78.7000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >4.08</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td></tr><tr><td width=138  valign=center  style="width:69.2500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=317  align=center  style="margin-left:42.3000pt;text-indent:-21.0000pt;mso-char-indent-count:0.0000;
text-align:center;mso-list:l16 level1 lfo27;" ><![if !supportLists]><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><span style='mso-list:Ignore;' >2<span>&nbsp;</span></span></span><![endif]><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=147  valign=center  style="width:73.7000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" >28023</span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:SimSun;font-size:11.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:SimSun;font-size:11.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >16.024</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=172  valign=center  style="width:86.2500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" >15.936</span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >23.945</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=150  valign=center  style="width:75.3000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >0.44</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=157  valign=center  style="width:78.7000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >4.12</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td></tr><tr><td width=138  valign=center  style="width:69.2500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=317  align=center  style="margin-left:42.3000pt;text-indent:-21.0000pt;mso-char-indent-count:0.0000;
text-align:center;mso-list:l16 level1 lfo27;" ><![if !supportLists]><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><span style='mso-list:Ignore;' >3<span>&nbsp;</span></span></span><![endif]><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=147  valign=center  style="width:73.7000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" >31823</span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:SimSun;font-size:11.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:SimSun;font-size:11.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >16.031</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=172  valign=center  style="width:86.2500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" >15.941</span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >23.94</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=150  valign=center  style="width:75.3000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p>&nbsp;</o:p></span></p></td><td width=157  valign=center  style="width:78.7000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p>&nbsp;</o:p></span></p></td></tr><tr><td width=138  valign=center  style="width:69.2500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=317  align=center  style="margin-left:42.3000pt;text-indent:-21.0000pt;mso-char-indent-count:0.0000;
text-align:center;mso-list:l16 level1 lfo27;" ><![if !supportLists]><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><span style='mso-list:Ignore;' >4<span>&nbsp;</span></span></span><![endif]><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=147  valign=center  style="width:73.7000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" >32523</span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:SimSun;font-size:11.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:SimSun;font-size:11.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >16.015</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=172  valign=center  style="width:86.2500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" >15.941</span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >23.941</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=150  valign=center  style="width:75.3000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >0.43</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=157  valign=center  style="width:78.7000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >4.1</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td></tr><tr><td width=138  valign=center  style="width:69.2500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=317  align=center  style="margin-left:42.3000pt;text-indent:-21.0000pt;mso-char-indent-count:0.0000;
text-align:center;mso-list:l16 level1 lfo27;" ><![if !supportLists]><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><span style='mso-list:Ignore;' >5<span>&nbsp;</span></span></span><![endif]><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=147  valign=center  style="width:73.7000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" >33123</span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:SimSun;font-size:11.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:SimSun;font-size:11.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >16.018</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=172  valign=center  style="width:86.2500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" >15.937</span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >23.943</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=150  valign=center  style="width:75.3000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >0.44</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=157  valign=center  style="width:78.7000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >4.05</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td></tr><tr><td width=138  valign=center  style="width:69.2500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=317  align=center  style="margin-left:42.3000pt;text-indent:-21.0000pt;mso-char-indent-count:0.0000;
text-align:center;mso-list:l16 level1 lfo27;" ><![if !supportLists]><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><span style='mso-list:Ignore;' >6<span>&nbsp;</span></span></span><![endif]><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=147  valign=center  style="width:73.7000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" >33423</span><span style="font-family:SimSun;color:rgb(0,0,0);font-size:11.0000pt;
mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:SimSun;font-size:11.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:SimSun;font-size:11.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p>&nbsp;</o:p></span></p></td><td width=172  valign=center  style="width:86.2500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p>&nbsp;</o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >23.946</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=150  valign=center  style="width:75.3000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p>&nbsp;</o:p></span></p></td><td width=157  valign=center  style="width:78.7000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p>&nbsp;</o:p></span></p></td></tr><tr><td width=138  valign=center  style="width:69.2500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=317  align=center  style="margin-left:42.3000pt;text-indent:-21.0000pt;mso-char-indent-count:0.0000;
text-align:center;mso-list:l16 level1 lfo27;" ><![if !supportLists]><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><span style='mso-list:Ignore;' >7<span>&nbsp;</span></span></span><![endif]><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=147  valign=center  style="width:73.7000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" >33524</span><span style="font-family:SimSun;color:rgb(0,0,0);font-size:11.0000pt;
mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:SimSun;font-size:11.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:SimSun;font-size:11.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >16.022</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=172  valign=center  style="width:86.2500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" >15.942</span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >23.938</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=150  valign=center  style="width:75.3000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >0.42</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=157  valign=center  style="width:78.7000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >4.07</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td></tr><tr><td width=138  valign=center  style="width:69.2500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=317  align=center  style="margin-left:42.3000pt;text-indent:-21.0000pt;mso-char-indent-count:0.0000;
text-align:center;mso-list:l16 level1 lfo27;" ><![if !supportLists]><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><span style='mso-list:Ignore;' >8<span>&nbsp;</span></span></span><![endif]><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=147  valign=center  style="width:73.7000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" >33824</span><span style="font-family:SimSun;color:rgb(0,0,0);font-size:11.0000pt;
mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:SimSun;font-size:11.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:SimSun;font-size:11.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >16.023</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=172  valign=center  style="width:86.2500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" >15.939</span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >23.952</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=150  valign=center  style="width:75.3000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >0.41</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=157  valign=center  style="width:78.7000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >4.06</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td></tr><tr><td width=138  valign=center  style="width:69.2500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=317  align=center  style="margin-left:42.3000pt;text-indent:-21.0000pt;mso-char-indent-count:0.0000;
text-align:center;mso-list:l16 level1 lfo27;" ><![if !supportLists]><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><span style='mso-list:Ignore;' >9<span>&nbsp;</span></span></span><![endif]><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=147  valign=center  style="width:73.7000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" >33923</span><span style="font-family:SimSun;color:rgb(0,0,0);font-size:11.0000pt;
mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:SimSun;font-size:11.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:SimSun;font-size:11.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >16.016</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=172  valign=center  style="width:86.2500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" >15.937</span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >23.937</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=150  valign=center  style="width:75.3000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >0.44</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=157  valign=center  style="width:78.7000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >4.11</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td></tr><tr><td width=138  valign=center  style="width:69.2500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=317  align=center  style="margin-left:42.3000pt;text-indent:-21.0000pt;mso-char-indent-count:0.0000;
text-align:center;mso-list:l16 level1 lfo27;" ><![if !supportLists]><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><span style='mso-list:Ignore;' >10<span>&nbsp;</span></span></span><![endif]><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=147  valign=center  style="width:73.7000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" >34124</span><span style="font-family:SimSun;color:rgb(0,0,0);font-size:11.0000pt;
mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:SimSun;font-size:11.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:SimSun;font-size:11.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >16.022</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=172  valign=center  style="width:86.2500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" >15.944</span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >23.946</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=150  valign=center  style="width:75.3000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >0.42</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=157  valign=center  style="width:78.7000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >4.07</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td></tr><tr><td width=138  valign=center  style="width:69.2500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=317  align=center  style="margin-left:42.3000pt;text-indent:-21.0000pt;mso-char-indent-count:0.0000;
text-align:center;mso-list:l16 level1 lfo27;" ><![if !supportLists]><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><span style='mso-list:Ignore;' >11<span>&nbsp;</span></span></span><![endif]><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=147  valign=center  style="width:73.7000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" >34223</span><span style="font-family:SimSun;color:rgb(0,0,0);font-size:11.0000pt;
mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:SimSun;font-size:11.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:SimSun;font-size:11.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >16.027</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=172  valign=center  style="width:86.2500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" >15.939</span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >23.948</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=150  valign=center  style="width:75.3000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >0.4</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=157  valign=center  style="width:78.7000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >4.04</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td></tr><tr><td width=138  valign=center  style="width:69.2500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=317  align=center  style="margin-left:42.3000pt;text-indent:-21.0000pt;mso-char-indent-count:0.0000;
text-align:center;mso-list:l16 level1 lfo27;" ><![if !supportLists]><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><span style='mso-list:Ignore;' >12<span>&nbsp;</span></span></span><![endif]><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=147  valign=center  style="width:73.7000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" >34524</span><span style="font-family:SimSun;color:rgb(0,0,0);font-size:11.0000pt;
mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:SimSun;font-size:11.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:SimSun;font-size:11.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >16.015</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=172  valign=center  style="width:86.2500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" >15.942</span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >23.944</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=150  valign=center  style="width:75.3000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >0.44</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=157  valign=center  style="width:78.7000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >4.15</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td></tr><tr><td width=138  valign=center  style="width:69.2500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=317  align=center  style="margin-left:42.3000pt;text-indent:-21.0000pt;mso-char-indent-count:0.0000;
text-align:center;mso-list:l16 level1 lfo27;" ><![if !supportLists]><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><span style='mso-list:Ignore;' >13<span>&nbsp;</span></span></span><![endif]><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=147  valign=center  style="width:73.7000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" >35124</span><span style="font-family:SimSun;color:rgb(0,0,0);font-size:11.0000pt;
mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:SimSun;font-size:11.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:SimSun;font-size:11.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >16.025</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=172  valign=center  style="width:86.2500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" >15.942</span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >23.952</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=150  valign=center  style="width:75.3000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >0.45</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=157  valign=center  style="width:78.7000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >4.08</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td></tr><tr><td width=138  valign=center  style="width:69.2500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=317  align=center  style="margin-left:42.3000pt;text-indent:-21.0000pt;mso-char-indent-count:0.0000;
text-align:center;mso-list:l16 level1 lfo27;" ><![if !supportLists]><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><span style='mso-list:Ignore;' >14<span>&nbsp;</span></span></span><![endif]><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=147  valign=center  style="width:73.7000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" >35824</span><span style="font-family:SimSun;color:rgb(0,0,0);font-size:11.0000pt;
mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:SimSun;font-size:11.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:SimSun;font-size:11.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >16.023</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=172  valign=center  style="width:86.2500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" >15.942</span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >23.946</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=150  valign=center  style="width:75.3000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >0.45</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=157  valign=center  style="width:78.7000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >4.03</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td></tr><tr><td width=138  valign=center  style="width:69.2500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=317  align=center  style="margin-left:42.3000pt;text-indent:-21.0000pt;mso-char-indent-count:0.0000;
text-align:center;mso-list:l16 level1 lfo27;" ><![if !supportLists]><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><span style='mso-list:Ignore;' >15<span>&nbsp;</span></span></span><![endif]><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=147  valign=center  style="width:73.7000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" >36024</span><span style="font-family:SimSun;color:rgb(0,0,0);font-size:11.0000pt;
mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:SimSun;font-size:11.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:SimSun;font-size:11.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >16.018</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=172  valign=center  style="width:86.2500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" >15.942</span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >23.948</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=150  valign=center  style="width:75.3000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >0.4</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=157  valign=center  style="width:78.7000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >4.08</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td></tr><tr><td width=138  valign=center  style="width:69.2500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=317  align=center  style="margin-left:42.3000pt;text-indent:-21.0000pt;mso-char-indent-count:0.0000;
text-align:center;mso-list:l16 level1 lfo27;" ><![if !supportLists]><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><span style='mso-list:Ignore;' >16<span>&nbsp;</span></span></span><![endif]><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=147  valign=center  style="width:73.7000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" >36123</span><span style="font-family:SimSun;color:rgb(0,0,0);font-size:11.0000pt;
mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:SimSun;font-size:11.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:SimSun;font-size:11.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >16.023</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=172  valign=center  style="width:86.2500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" >15.937</span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >23.957</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=150  valign=center  style="width:75.3000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >0.44</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=157  valign=center  style="width:78.7000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >4.08</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td></tr><tr><td width=138  valign=center  style="width:69.2500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=317  align=center  style="margin-left:42.3000pt;text-indent:-21.0000pt;mso-char-indent-count:0.0000;
text-align:center;mso-list:l16 level1 lfo27;" ><![if !supportLists]><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><span style='mso-list:Ignore;' >17<span>&nbsp;</span></span></span><![endif]><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=147  valign=center  style="width:73.7000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" >36124</span><span style="font-family:SimSun;color:rgb(0,0,0);font-size:11.0000pt;
mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:SimSun;font-size:11.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:SimSun;font-size:11.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >16.02</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=172  valign=center  style="width:86.2500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" >15.942</span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >23.938</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=150  valign=center  style="width:75.3000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >0.44</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=157  valign=center  style="width:78.7000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >4.02</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td></tr><tr><td width=138  valign=center  style="width:69.2500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=317  align=center  style="margin-left:42.3000pt;text-indent:-21.0000pt;mso-char-indent-count:0.0000;
text-align:center;mso-list:l16 level1 lfo27;" ><![if !supportLists]><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><span style='mso-list:Ignore;' >18<span>&nbsp;</span></span></span><![endif]><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=147  valign=center  style="width:73.7000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" >36223</span><span style="font-family:SimSun;color:rgb(0,0,0);font-size:11.0000pt;
mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:SimSun;font-size:11.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:SimSun;font-size:11.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >16.024</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=172  valign=center  style="width:86.2500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" >15.938</span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >23.94</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=150  valign=center  style="width:75.3000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >0.44</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=157  valign=center  style="width:78.7000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >4.03</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td></tr><tr><td width=138  valign=center  style="width:69.2500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=317  align=center  style="margin-left:42.3000pt;text-indent:-21.0000pt;mso-char-indent-count:0.0000;
text-align:center;mso-list:l16 level1 lfo27;" ><![if !supportLists]><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><span style='mso-list:Ignore;' >19<span>&nbsp;</span></span></span><![endif]><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=147  valign=center  style="width:73.7000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" >36824</span><span style="font-family:SimSun;color:rgb(0,0,0);font-size:11.0000pt;
mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:SimSun;font-size:11.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:SimSun;font-size:11.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >16.023</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=172  valign=center  style="width:86.2500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" >15.94</span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >23.944</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=150  valign=center  style="width:75.3000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >0.43</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=157  valign=center  style="width:78.7000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >4.02</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td></tr><tr><td width=138  valign=center  style="width:69.2500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=317  align=center  style="margin-left:42.3000pt;text-indent:-21.0000pt;mso-char-indent-count:0.0000;
text-align:center;mso-list:l16 level1 lfo27;" ><![if !supportLists]><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><span style='mso-list:Ignore;' >20<span>&nbsp;</span></span></span><![endif]><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=147  valign=center  style="width:73.7000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" >37124</span><span style="font-family:SimSun;color:rgb(0,0,0);font-size:11.0000pt;
mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:SimSun;font-size:11.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:SimSun;font-size:11.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >16.018</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=172  valign=center  style="width:86.2500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" >15.942</span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >23.939</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=150  valign=center  style="width:75.3000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >0.43</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=157  valign=center  style="width:78.7000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >4.06</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td></tr><tr><td width=138  valign=center  style="width:69.2500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=317  align=center  style="margin-left:42.3000pt;text-indent:-21.0000pt;mso-char-indent-count:0.0000;
text-align:center;mso-list:l16 level1 lfo27;" ><![if !supportLists]><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><span style='mso-list:Ignore;' >21<span>&nbsp;</span></span></span><![endif]><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=147  valign=center  style="width:73.7000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" >37323</span><span style="font-family:SimSun;color:rgb(0,0,0);font-size:11.0000pt;
mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:SimSun;font-size:11.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:SimSun;font-size:11.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >16.023</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=172  valign=center  style="width:86.2500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" >15.938</span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >23.942</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=150  valign=center  style="width:75.3000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >0.44</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=157  valign=center  style="width:78.7000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >4.06</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td></tr><tr><td width=138  valign=center  style="width:69.2500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=317  align=center  style="margin-left:42.3000pt;text-indent:-21.0000pt;mso-char-indent-count:0.0000;
text-align:center;mso-list:l16 level1 lfo27;" ><![if !supportLists]><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><span style='mso-list:Ignore;' >22<span>&nbsp;</span></span></span><![endif]><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=147  valign=center  style="width:73.7000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" >37424</span><span style="font-family:SimSun;color:rgb(0,0,0);font-size:11.0000pt;
mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:SimSun;font-size:11.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:SimSun;font-size:11.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >16.024</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=172  valign=center  style="width:86.2500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" >15.936</span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >23.938</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=150  valign=center  style="width:75.3000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >0.44</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=157  valign=center  style="width:78.7000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >4.07</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td></tr><tr><td width=138  valign=center  style="width:69.2500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=317  align=center  style="margin-left:42.3000pt;text-indent:-21.0000pt;mso-char-indent-count:0.0000;
text-align:center;mso-list:l16 level1 lfo27;" ><![if !supportLists]><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><span style='mso-list:Ignore;' >23<span>&nbsp;</span></span></span><![endif]><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=147  valign=center  style="width:73.7000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" >37524</span><span style="font-family:SimSun;color:rgb(0,0,0);font-size:11.0000pt;
mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:SimSun;font-size:11.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:SimSun;font-size:11.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >16.02</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=172  valign=center  style="width:86.2500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" >15.939</span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >23.94</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=150  valign=center  style="width:75.3000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >0.42</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=157  valign=center  style="width:78.7000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >4.07</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td></tr><tr><td width=138  valign=center  style="width:69.2500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=317  align=center  style="margin-left:42.3000pt;text-indent:-21.0000pt;mso-char-indent-count:0.0000;
text-align:center;mso-list:l16 level1 lfo27;" ><![if !supportLists]><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><span style='mso-list:Ignore;' >24<span>&nbsp;</span></span></span><![endif]><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=147  valign=center  style="width:73.7000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" >37623</span><span style="font-family:SimSun;color:rgb(0,0,0);font-size:11.0000pt;
mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:SimSun;font-size:11.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:SimSun;font-size:11.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >16.032</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=172  valign=center  style="width:86.2500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" >15.943</span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >23.94</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=150  valign=center  style="width:75.3000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >0.4</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=157  valign=center  style="width:78.7000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >4.06</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td></tr><tr><td width=138  valign=center  style="width:69.2500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=317  align=center  style="margin-left:42.3000pt;text-indent:-21.0000pt;mso-char-indent-count:0.0000;
text-align:center;mso-list:l16 level1 lfo27;" ><![if !supportLists]><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><span style='mso-list:Ignore;' >25<span>&nbsp;</span></span></span><![endif]><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=147  valign=center  style="width:73.7000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" >37623</span><span style="font-family:SimSun;color:rgb(0,0,0);font-size:11.0000pt;
mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:SimSun;font-size:11.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:SimSun;font-size:11.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >16.021</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=172  valign=center  style="width:86.2500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" >15.943</span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >23.946</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=150  valign=center  style="width:75.3000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >0.4</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=157  valign=center  style="width:78.7000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >4.16</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td></tr><tr><td width=138  valign=center  style="width:69.2500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=317  align=center  style="margin-left:42.3000pt;text-indent:-21.0000pt;mso-char-indent-count:0.0000;
text-align:center;mso-list:l16 level1 lfo27;" ><![if !supportLists]><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><span style='mso-list:Ignore;' >26<span>&nbsp;</span></span></span><![endif]><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=147  valign=center  style="width:73.7000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" >37724</span><span style="font-family:SimSun;color:rgb(0,0,0);font-size:11.0000pt;
mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:SimSun;font-size:11.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:SimSun;font-size:11.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >16.025</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=172  valign=center  style="width:86.2500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" >15.938</span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >23.94</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=150  valign=center  style="width:75.3000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >0.44</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=157  valign=center  style="width:78.7000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >4.07</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td></tr><tr><td width=138  valign=center  style="width:69.2500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=317  align=center  style="margin-left:42.3000pt;text-indent:-21.0000pt;mso-char-indent-count:0.0000;
text-align:center;mso-list:l16 level1 lfo27;" ><![if !supportLists]><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><span style='mso-list:Ignore;' >27<span>&nbsp;</span></span></span><![endif]><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=147  valign=center  style="width:73.7000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" >38223</span><span style="font-family:SimSun;color:rgb(0,0,0);font-size:11.0000pt;
mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:SimSun;font-size:11.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:SimSun;font-size:11.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >16.027</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=172  valign=center  style="width:86.2500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" >15.943</span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >23.958</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=150  valign=center  style="width:75.3000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >0.45</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=157  valign=center  style="width:78.7000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >4.1</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td></tr><tr><td width=138  valign=center  style="width:69.2500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=317  align=center  style="margin-left:42.3000pt;text-indent:-21.0000pt;mso-char-indent-count:0.0000;
text-align:center;mso-list:l16 level1 lfo27;" ><![if !supportLists]><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><span style='mso-list:Ignore;' >28<span>&nbsp;</span></span></span><![endif]><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=147  valign=center  style="width:73.7000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" >8424</span><span style="font-family:SimSun;color:rgb(0,0,0);font-size:11.0000pt;
mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:SimSun;font-size:11.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:SimSun;font-size:11.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >16.021</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=172  valign=center  style="width:86.2500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" >15.938</span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >23.947</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=150  valign=center  style="width:75.3000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >0.44</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=157  valign=center  style="width:78.7000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >4.05</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td></tr><tr><td width=138  valign=center  style="width:69.2500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=317  align=center  style="margin-left:42.3000pt;text-indent:-21.0000pt;mso-char-indent-count:0.0000;
text-align:center;mso-list:l16 level1 lfo27;" ><![if !supportLists]><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><span style='mso-list:Ignore;' >29<span>&nbsp;</span></span></span><![endif]><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=147  valign=center  style="width:73.7000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" >8524</span><span style="font-family:SimSun;color:rgb(0,0,0);font-size:11.0000pt;
mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:SimSun;font-size:11.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="mso-pagination:widow-orphan;text-align:center;vertical-align:middle;" ><span style="font-family:SimSun;font-size:11.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><span class="dynamic-data" data-source-id="attach-1-1-2-1">16.028</span></span>
<span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=172  valign=center  style="width:86.2500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" >15.94</span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=176  valign=center  style="width:88.4500pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >23.936</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=150  valign=center  style="width:75.3000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >0.4</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td><td width=157  valign=center  style="width:78.7000pt;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=right  style="mso-pagination:widow-orphan;text-align:right;vertical-align:middle;" ><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><font face="Arial Unicode MS" >4.03</font></span><span style="font-family:'Arial Unicode MS';color:rgb(0,0,0);font-style:normal;
font-size:10.0000pt;mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p></td></tr></table><p class=MsoNormalIndent ><span style="mso-spacerun:'yes';font-family:'Times New Roman';mso-fareast-font-family:SimHei;
font-size:12.0000pt;mso-font-kerning:0.0000pt;" ><font face="SimHei" >附表</font>24 &nbsp;<font face="SimHei" >特殊过程工艺质量控制情况统计表</font></span><span style="mso-spacerun:'yes';font-family:SimHei;font-size:12.0000pt;
mso-font-kerning:0.0000pt;" ><o:p></o:p></span></p><p class=MsoNormalIndent  style="text-indent:0.0000pt;" ><b style="mso-bidi-font-weight:normal" ><span style="mso-spacerun:'yes';font-family:SimSun;mso-ansi-font-weight:bold;
font-size:14.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></b></p><table class=MsoNormalTable  border=1  cellspacing=0  style="border-collapse:collapse;width:100.0000%;border:none;
mso-border-left-alt:0.5000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;mso-border-insideh:0.5000pt solid windowtext;mso-border-insidev:0.5000pt solid windowtext;
mso-padding-alt:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;" ><tr style="height:45.6500pt;" ><td width=100.0000%  valign=center  colspan=8  style="width:100.0000%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="text-align:center;" ><span style="font-family:SimHei;mso-bidi-font-weight:bold;font-size:14.0000pt;
mso-font-kerning:1.0000pt;" ><font face="SimHei" >特殊过程工艺质量控制情况统计表</font></span><span style="font-family:SimHei;mso-ascii-font-family:SimSun;mso-hansi-font-family:SimSun;
font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td></tr><tr><td width=4.5800%  valign=top  style="width:4.5800%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormalIndent  style="text-indent:0.0000pt;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >序号</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=12.5200%  valign=top  style="width:12.5200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormalIndent  style="text-indent:0.0000pt;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >产品图号</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=7.6800%  valign=top  style="width:7.6800%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormalIndent  style="text-indent:0.0000pt;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >产品名称</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=7.6800%  valign=top  style="width:7.6800%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormalIndent  style="text-indent:0.0000pt;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >生产单位</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=9.6400%  valign=top  style="width:9.6400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormalIndent  style="text-indent:0.0000pt;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >特殊过程</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=25.9600%  valign=center  style="width:25.9600%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="text-align:center;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >特殊过程确认及控制情况</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=15.8000%  valign=center  style="width:15.8000%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="text-align:center;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >旁证验证情况</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=16.1400%  valign=center  style="width:16.1400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:1.0000pt solid windowtext;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="text-align:center;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >备注</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td></tr><tr><td width=4.5800%  valign=top  style="width:4.5800%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormalIndent  style="text-indent:0.0000pt;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >1</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=12.5200%  valign=top  style="width:12.5200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormalIndent  style="text-indent:0.0000pt;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >XX-101</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=7.6800%  valign=top  style="width:7.6800%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormalIndent  style="text-indent:0.0000pt;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >壳体</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=7.6800%  valign=top  style="width:7.6800%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormalIndent  style="text-indent:0.0000pt;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >4</font><font face="SimSun" >车间</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=9.6400%  valign=top  style="width:9.6400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormalIndent  style="text-indent:0.0000pt;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >退火处理</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=25.9600%  valign=top  style="width:25.9600%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormalIndent  style="text-indent:0.0000pt;" ><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >按</font>QJ1181.1A<font face="SimSun" >进行真空或氢气保护高温退火（不允许在零件表面铺洒氧化铝或其他粉末），热处理后磁性能应符合</font><font face="Times New Roman" >GBn198-1988</font><font face="SimSun" >的要求</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=15.8000%  valign=top  style="width:15.8000%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormalIndent  style="text-indent:0.0000pt;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >对热处理随炉试片进行磁性能检测。</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p><p class=MsoNormal ><span style="font-family:'Times New Roman';font-size:9.0000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >&#956;0.4(mH/m)≥3.1 <span style="mso-spacerun:'yes';" >&nbsp;</span>8.4/8.9</font></span><span style="font-family:'Times New Roman';font-size:9.0000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p><p class=MsoNormal ><span style="font-family:'Times New Roman';font-size:9.0000pt;mso-font-kerning:1.0000pt;" >Hc(A/m)≤14.4 <span style="mso-spacerun:'yes';" >&nbsp;</span>4.8/5.2</span><span style="font-family:'Times New Roman';font-size:9.0000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p><p class=MsoNormal ><span style="font-family:'Times New Roman';font-size:9.0000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >&#956;m(mH/m)≥31.3 <span style="mso-spacerun:'yes';" >&nbsp;</span>70.8/74.1</font></span><span style="font-family:'Times New Roman';font-size:9.0000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p><p class=MsoNormalIndent  style="text-indent:0.0000pt;" ><span style="font-family:'Times New Roman';font-size:9.0000pt;mso-font-kerning:1.0000pt;" >Bs(T) <span style="mso-spacerun:'yes';" >&nbsp;</span>1.5</span><span style="font-family:'Times New Roman';font-size:9.0000pt;mso-font-kerning:1.0000pt;" >4</span><span style="font-family:'Times New Roman';font-size:9.0000pt;mso-font-kerning:1.0000pt;" >/1.5</span><span style="font-family:'Times New Roman';font-size:9.0000pt;mso-font-kerning:1.0000pt;" >4</span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=16.1400%  valign=center  style="width:16.1400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormalIndent  align=center  style="text-indent:0.0000pt;text-align:center;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >1323007273</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p><p class=MsoNormalIndent  align=center  style="text-indent:0.0000pt;text-align:center;" ><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" >0422012274</span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td></tr><tr><td width=4.5800%  valign=top  style="width:4.5800%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormalIndent  style="text-indent:0.0000pt;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >2</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=12.5200%  valign=top  style="width:12.5200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormalIndent  style="text-indent:0.0000pt;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >XX-104</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=7.6800%  valign=top  style="width:7.6800%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormalIndent  style="text-indent:0.0000pt;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >上盖</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=7.6800%  valign=top  style="width:7.6800%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormalIndent  style="text-indent:0.0000pt;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >4</font><font face="SimSun" >车间</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=9.6400%  valign=top  style="width:9.6400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormalIndent  style="text-indent:0.0000pt;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >退火处理</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=25.9600%  valign=top  style="width:25.9600%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormalIndent  style="text-indent:0.0000pt;" ><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >按</font>QJ1181.1A<font face="SimSun" >进行真空或氢气保护高温退火（不允许在零件表面铺洒氧化铝或其他粉末），热处理后磁性能应符合</font><font face="Times New Roman" >GBn198-1988</font><font face="SimSun" >的要求</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=15.8000%  valign=top  style="width:15.8000%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormalIndent  style="text-indent:0.0000pt;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >对热处理随炉试片进行磁性能检测。</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p><p class=MsoNormal ><span style="font-family:'Times New Roman';font-size:9.0000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >&#956;0.4(mH/m)≥3.1 <span style="mso-spacerun:'yes';" >&nbsp;</span>7.3/7.7</font></span><span style="font-family:'Times New Roman';font-size:9.0000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p><p class=MsoNormal ><span style="font-family:'Times New Roman';font-size:9.0000pt;mso-font-kerning:1.0000pt;" >Hc(A/m)≤14.4 <span style="mso-spacerun:'yes';" >&nbsp;</span>6.1/6.3</span><span style="font-family:'Times New Roman';font-size:9.0000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p><p class=MsoNormal ><span style="font-family:'Times New Roman';font-size:9.0000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >&#956;m(mH/m)≥31.3</font></span><span style="font-family:'Times New Roman';font-size:9.0000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p><p class=MsoNormal ><span style="font-family:'Times New Roman';font-size:9.0000pt;mso-font-kerning:1.0000pt;" >38.0/39.1 </span><span style="font-family:'Times New Roman';font-size:9.0000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p><p class=MsoNormalIndent  style="text-indent:0.0000pt;" ><span style="font-family:'Times New Roman';font-size:9.0000pt;mso-font-kerning:1.0000pt;" >Bs(T) <span style="mso-spacerun:'yes';" >&nbsp;</span>1.5</span><span style="font-family:'Times New Roman';font-size:9.0000pt;mso-font-kerning:1.0000pt;" >3</span><span style="font-family:'Times New Roman';font-size:9.0000pt;mso-font-kerning:1.0000pt;" >/1.5</span><span style="font-family:'Times New Roman';font-size:9.0000pt;mso-font-kerning:1.0000pt;" >3</span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=16.1400%  valign=center  style="width:16.1400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormalIndent  align=center  style="text-indent:0.0000pt;text-align:center;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >1321003820</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p><p class=MsoNormalIndent  align=center  style="text-indent:0.0000pt;text-align:center;" ><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" >0421007956</span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td></tr><tr><td width=4.5800%  valign=top  style="width:4.5800%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormalIndent  style="text-indent:0.0000pt;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >3</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=12.5200%  valign=top  style="width:12.5200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormalIndent  style="text-indent:0.0000pt;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >XX-1211</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=7.6800%  valign=top  style="width:7.6800%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormalIndent  style="text-indent:0.0000pt;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >挡铁</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=7.6800%  valign=top  style="width:7.6800%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormalIndent  style="text-indent:0.0000pt;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >4</font><font face="SimSun" >车间</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=9.6400%  valign=top  style="width:9.6400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormalIndent  style="text-indent:0.0000pt;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >退火处理</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=25.9600%  valign=top  style="width:25.9600%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormalIndent  style="text-indent:0.0000pt;" ><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >按</font>QJ1181.1A<font face="SimSun" >进行氢气保护高温退火（不允许在零件表面铺洒氧化铝或其他粉末），热处理后磁性能应符合</font><font face="Times New Roman" >GBn198-1988</font><font face="SimSun" >的要求</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=15.8000%  valign=top  style="width:15.8000%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormalIndent  style="text-indent:0.0000pt;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >对热处理随炉试片进行磁性能检测。</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p><p class=MsoNormal ><span style="font-family:'Times New Roman';font-size:9.0000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >&#956;0.4(mH/m)≥3.1 <span style="mso-spacerun:'yes';" >&nbsp;</font></span></span><span style="font-family:SimSun;font-size:9.0000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >15.2</font></span><span style="font-family:'Times New Roman';font-size:9.0000pt;mso-font-kerning:1.0000pt;" >/</span><span style="font-family:SimSun;font-size:9.0000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >9.5</font></span><span style="font-family:'Times New Roman';font-size:9.0000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p><p class=MsoNormal ><span style="font-family:'Times New Roman';font-size:9.0000pt;mso-font-kerning:1.0000pt;" >Hc(A/m)≤14.4 <span style="mso-spacerun:'yes';" >&nbsp;</span></span><span style="font-family:SimSun;font-size:9.0000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >2.2</font></span><span style="font-family:'Times New Roman';font-size:9.0000pt;mso-font-kerning:1.0000pt;" >/</span><span style="font-family:SimSun;font-size:9.0000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >2.6</font></span><span style="font-family:'Times New Roman';font-size:9.0000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p><p class=MsoNormal ><span style="font-family:'Times New Roman';font-size:9.0000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >&#956;m(mH/m)≥31.3</font></span><span style="font-family:'Times New Roman';font-size:9.0000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p><p class=MsoNormal ><span style="font-family:SimSun;font-size:9.0000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >162.9</font></span><span style="font-family:'Times New Roman';font-size:9.0000pt;mso-font-kerning:1.0000pt;" >/</span><span style="font-family:SimSun;font-size:9.0000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >172.1</font></span><span style="font-family:'Times New Roman';font-size:9.0000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p><p class=MsoNormalIndent  style="text-indent:0.0000pt;" ><span style="font-family:'Times New Roman';font-size:9.0000pt;mso-font-kerning:1.0000pt;" >Bs(T) <span style="mso-spacerun:'yes';" >&nbsp;</span>1.5</span><span style="font-family:SimSun;font-size:9.0000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >5</font></span><span style="font-family:'Times New Roman';font-size:9.0000pt;mso-font-kerning:1.0000pt;" >/1.5</span><span style="font-family:SimSun;font-size:9.0000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >6</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=16.1400%  valign=center  style="width:16.1400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormalIndent  align=center  style="text-indent:0.0000pt;text-align:center;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >1321004543</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p><p class=MsoNormalIndent  align=center  style="text-indent:0.0000pt;text-align:center;" ><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" >0421010026</span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td></tr><tr><td width=4.5800%  valign=top  style="width:4.5800%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormalIndent  style="text-indent:0.0000pt;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >4</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=12.5200%  valign=top  style="width:12.5200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormalIndent  style="text-indent:0.0000pt;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >XX-1213</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=7.6800%  valign=top  style="width:7.6800%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormalIndent  style="text-indent:0.0000pt;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >导磁环</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=7.6800%  valign=top  style="width:7.6800%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormalIndent  style="text-indent:0.0000pt;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >4</font><font face="SimSun" >车间</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=9.6400%  valign=top  style="width:9.6400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormalIndent  style="text-indent:0.0000pt;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >退火处理</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=25.9600%  valign=top  style="width:25.9600%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormalIndent  style="text-indent:0.0000pt;" ><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >按</font>QJ1181.1A<font face="SimSun" >进行氢气保护高温退火（不允许在零件表面铺洒氧化铝或其他粉末），热处理后磁性能应符合</font><font face="Times New Roman" >GBn198-1988</font><font face="SimSun" >的要求</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=15.8000%  valign=top  style="width:15.8000%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormalIndent  style="text-indent:0.0000pt;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >对热处理随炉试片进行磁性能检测。</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p><p class=MsoNormal ><span style="font-family:'Times New Roman';font-size:9.0000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >&#956;0.4(mH/m)≥3.1 <span style="mso-spacerun:'yes';" >&nbsp;</font></span></span><span style="font-family:SimSun;font-size:9.0000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >12.2</font></span><span style="font-family:'Times New Roman';font-size:9.0000pt;mso-font-kerning:1.0000pt;" >/</span><span style="font-family:SimSun;font-size:9.0000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >12.6</font></span><span style="font-family:'Times New Roman';font-size:9.0000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p><p class=MsoNormal ><span style="font-family:'Times New Roman';font-size:9.0000pt;mso-font-kerning:1.0000pt;" >Hc(A/m)≤14.4 <span style="mso-spacerun:'yes';" >&nbsp;</span></span><span style="font-family:SimSun;font-size:9.0000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >2.4</font></span><span style="font-family:'Times New Roman';font-size:9.0000pt;mso-font-kerning:1.0000pt;" >/</span><span style="font-family:SimSun;font-size:9.0000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >2.5</font></span><span style="font-family:'Times New Roman';font-size:9.0000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p><p class=MsoNormal ><span style="font-family:'Times New Roman';font-size:9.0000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >&#956;m(mH/m)≥31.3</font></span><span style="font-family:'Times New Roman';font-size:9.0000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p><p class=MsoNormal ><span style="font-family:SimSun;font-size:9.0000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >161.9</font></span><span style="font-family:'Times New Roman';font-size:9.0000pt;mso-font-kerning:1.0000pt;" >/</span><span style="font-family:SimSun;font-size:9.0000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >162.1</font></span><span style="font-family:'Times New Roman';font-size:9.0000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p><p class=MsoNormalIndent  style="text-indent:0.0000pt;" ><span style="font-family:'Times New Roman';font-size:9.0000pt;mso-font-kerning:1.0000pt;" >Bs(T) <span style="mso-spacerun:'yes';" >&nbsp;</span>1.5</span><span style="font-family:SimSun;font-size:9.0000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >6</font></span><span style="font-family:'Times New Roman';font-size:9.0000pt;mso-font-kerning:1.0000pt;" >/1.5</span><span style="font-family:SimSun;font-size:9.0000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >7</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=16.1400%  valign=center  style="width:16.1400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormalIndent  align=center  style="text-indent:0.0000pt;text-align:center;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >1321004540</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p><p class=MsoNormalIndent  align=center  style="text-indent:0.0000pt;text-align:center;" ><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" >0421011462</span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td></tr><tr><td width=4.5800%  valign=top  style="width:4.5800%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormalIndent  style="text-indent:0.0000pt;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >5</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=12.5200%  valign=top  style="width:12.5200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormalIndent  style="text-indent:0.0000pt;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >XX-1210</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=7.6800%  valign=top  style="width:7.6800%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormalIndent  style="text-indent:0.0000pt;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >套筒毛坯</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=7.6800%  valign=top  style="width:7.6800%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormalIndent  style="text-indent:0.0000pt;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >104</font><font face="SimSun" >车间</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=9.6400%  valign=top  style="width:9.6400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormalIndent  style="text-indent:0.0000pt;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >电子束焊</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=25.9600%  valign=top  style="width:25.9600%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  style="text-align:left;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >1、焊接人员确认：操作人员具备军品上岗证和设备操作证，持证上岗；</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p><p class=MsoNormal  style="text-align:left;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >2、焊接设备及工装状态确认：设备运行正常、工作稳定，工装状态良好；</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p><p class=MsoNormal  style="text-align:left;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >3、焊接用辅助材料确定：清洁剂均有合格证明；</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p><p class=MsoNormal  style="text-align:left;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >4、焊接方法及产品状态确认：</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p><p class=MsoNormalIndent  style="text-indent:0.0000pt;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >5、焊缝质量检测结果确认：焊缝外观连续、无凹陷，熔深及内部质量满足要求。</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=15.8000%  valign=center  style="width:15.8000%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormal  align=center  style="text-align:center;line-height:12.0000pt;mso-line-height-rule:exactly;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >剖切检查代替</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" >X</span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >射线检测。对焊接首件进行剖切检查，沿轴线平均切成</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" >8</span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >瓣，检查</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" >8</span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >个截面的熔深和焊缝质量。</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p><p class=MsoNormal  align=center  style="text-align:center;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >剖切报告：</font><font face="SimSun" >21BJ1-09919，21BJ1-10712</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=16.1400%  valign=center  style="width:16.1400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=279  align=center  style="text-align:center;" ><span style="font-family:'Times New Roman';letter-spacing:-0.2000pt;font-size:10.5000pt;
mso-font-kerning:10.5000pt;" >10421000546</span><span style="font-family:SimSun;letter-spacing:-0.2000pt;font-size:10.5000pt;
mso-font-kerning:10.5000pt;" ><o:p></o:p></span></p><p class=279  align=center  style="text-align:center;" ><span style="font-family:SimSun;letter-spacing:-0.2000pt;font-size:10.5000pt;
mso-font-kerning:10.5000pt;" ><font face="Times New Roman" >/10421000467</font></span><span style="font-family:'Times New Roman';letter-spacing:-0.2000pt;font-size:10.5000pt;
mso-font-kerning:10.5000pt;" ><o:p></o:p></span></p></td></tr><tr><td width=4.5800%  valign=top  style="width:4.5800%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormalIndent  style="text-indent:0.0000pt;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >6</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=12.5200%  valign=top  style="width:12.5200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormalIndent  style="text-indent:0.0000pt;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >XX-120</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=7.6800%  valign=top  style="width:7.6800%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormalIndent  style="text-indent:0.0000pt;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >套筒</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=7.6800%  valign=top  style="width:7.6800%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormalIndent  style="text-indent:0.0000pt;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >4</font><font face="SimSun" >车间</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=9.6400%  valign=top  style="width:9.6400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormalIndent  style="text-indent:0.0000pt;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >退火处理</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=25.9600%  valign=top  style="width:25.9600%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormalIndent  style="text-indent:0.0000pt;" ><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >按</font>QJ1181.1A<font face="SimSun" >进行真空或氢气保护高温退火（不允许在零件表面铺洒氧化铝或其他粉末），热处理后磁性能应符合</font><font face="Times New Roman" >GBn198-1988</font><font face="SimSun" >的要求</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=15.8000%  valign=top  style="width:15.8000%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormalIndent  style="text-indent:0.0000pt;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >对热处理随炉试片进行磁性能检测。</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p><p class=MsoNormal ><span style="font-family:'Times New Roman';font-size:9.0000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >&#956;0.4(mH/m)≥3.1 <span style="mso-spacerun:'yes';" >&nbsp;</font></span></span><span style="font-family:SimSun;font-size:9.0000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >8.5</font></span><span style="font-family:'Times New Roman';font-size:9.0000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p><p class=MsoNormal ><span style="font-family:'Times New Roman';font-size:9.0000pt;mso-font-kerning:1.0000pt;" >Hc(A/m)≤14.4 <span style="mso-spacerun:'yes';" >&nbsp;</span></span><span style="font-family:SimSun;font-size:9.0000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >2.9</font></span><span style="font-family:'Times New Roman';font-size:9.0000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p><p class=MsoNormal ><span style="font-family:'Times New Roman';font-size:9.0000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >&#956;m(mH/m)≥31.3</font></span><span style="font-family:'Times New Roman';font-size:9.0000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p><p class=MsoNormal ><span style="font-family:SimSun;font-size:9.0000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >105.0</font></span><span style="font-family:'Times New Roman';font-size:9.0000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p><p class=MsoNormalIndent  style="text-indent:0.0000pt;" ><span style="font-family:'Times New Roman';font-size:9.0000pt;mso-font-kerning:1.0000pt;" >Bs(T) <span style="mso-spacerun:'yes';" >&nbsp;</span>1.5</span><span style="font-family:SimSun;font-size:9.0000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >4</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=16.1400%  valign=center  style="width:16.1400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormalIndent  align=center  style="text-indent:0.0000pt;text-align:center;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >1323008285/1323008284</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p><p class=MsoNormalIndent  align=center  style="text-indent:0.0000pt;text-align:center;" ><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" >0423008408</span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >/</font></span><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" >0423008407</span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td></tr><tr><td width=4.5800%  valign=top  style="width:4.5800%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormalIndent  style="text-indent:0.0000pt;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >7</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=12.5200%  valign=top  style="width:12.5200%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormalIndent  style="text-indent:0.0000pt;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >XX-211</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=7.6800%  valign=top  style="width:7.6800%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormalIndent  style="text-indent:0.0000pt;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >衔铁骨架</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=7.6800%  valign=top  style="width:7.6800%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormalIndent  style="text-indent:0.0000pt;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >4</font><font face="SimSun" >车间</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=9.6400%  valign=top  style="width:9.6400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormalIndent  style="text-indent:0.0000pt;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >退火处理</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=25.9600%  valign=top  style="width:25.9600%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormalIndent  style="text-indent:0.0000pt;" ><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >按</font>QJ1181.1A<font face="SimSun" >进行真空或氢气保护高温退火（不允许在零件表面铺洒氧化铝或其他粉末），热处理后磁性能应符合</font><font face="Times New Roman" >GBn198-1988</font><font face="SimSun" >的要求</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=15.8000%  valign=top  style="width:15.8000%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormalIndent  style="text-indent:0.0000pt;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="SimSun" >对热处理随炉试片进行磁性能检测。</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p><p class=MsoNormal ><span style="font-family:'Times New Roman';font-size:9.0000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >&#956;0.4(mH/m)≥3</font></span><span style="font-family:SimSun;font-size:9.0000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >.</font></span><span style="font-family:'Times New Roman';font-size:9.0000pt;mso-font-kerning:1.0000pt;" >1</span><span style="font-family:SimSun;font-size:9.0000pt;mso-font-kerning:1.0000pt;" ><span style="font-family:'Times New Roman';mso-spacerun:'yes';" >&nbsp;&nbsp;</span><font face="Times New Roman" >7.1/9.2</font></span><span style="font-family:SimSun;font-size:9.0000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p><p class=MsoNormal ><span style="font-family:'Times New Roman';font-size:9.0000pt;mso-font-kerning:1.0000pt;" >Hc(A/m)≤14.4 </span><span style="font-family:SimSun;font-size:9.0000pt;mso-font-kerning:1.0000pt;" ><span style="font-family:'Times New Roman';mso-spacerun:'yes';" >&nbsp;</span><font face="Times New Roman" >4.5/3.7</font></span><span style="font-family:SimSun;font-size:9.0000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p><p class=MsoNormal ><span style="font-family:'Times New Roman';font-size:9.0000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >&#956;m(mH/m)≥31.3</font></span><span style="font-family:SimSun;font-size:9.0000pt;mso-font-kerning:1.0000pt;" ><span style="font-family:'Times New Roman';mso-spacerun:'yes';" >&nbsp;&nbsp;</span><font face="Times New Roman" >60.6/51.6</font></span><span style="font-family:SimSun;font-size:9.0000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p><p class=MsoNormal ><span style="font-family:'Times New Roman';font-size:9.0000pt;mso-font-kerning:1.0000pt;" >Bs(T) </span><span style="font-family:SimSun;font-size:9.0000pt;mso-font-kerning:1.0000pt;" ><span style="font-family:'Times New Roman';mso-spacerun:'yes';" >&nbsp;</span><font face="Times New Roman" >1.52/1.54</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td><td width=16.1400%  valign=center  style="width:16.1400%;padding:0.0000pt 5.4000pt 0.0000pt 5.4000pt ;border-left:1.0000pt solid windowtext;
mso-border-left-alt:0.5000pt solid windowtext;border-right:1.0000pt solid windowtext;mso-border-right-alt:0.5000pt solid windowtext;
border-top:none;mso-border-top-alt:0.5000pt solid windowtext;border-bottom:1.0000pt solid windowtext;
mso-border-bottom-alt:0.5000pt solid windowtext;" ><p class=MsoNormalIndent  align=center  style="text-indent:0.0000pt;text-align:center;" ><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><font face="Times New Roman" >1322000931</font></span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p><p class=MsoNormalIndent  align=center  style="text-indent:0.0000pt;text-align:center;" ><span style="font-family:'Times New Roman';font-size:10.5000pt;mso-font-kerning:1.0000pt;" >0422001332</span><span style="font-family:SimSun;font-size:10.5000pt;mso-font-kerning:1.0000pt;" ><o:p></o:p></span></p></td></tr></table><p class=MsoNormalIndent  style="text-indent:0.0000pt;" ><b style="mso-bidi-font-weight:normal" ><span style="mso-spacerun:'yes';font-family:SimSun;mso-ansi-font-weight:bold;
font-size:14.0000pt;mso-font-kerning:1.0000pt;" ><o:p>&nbsp;</o:p></span></b></p></div><!--EndFragment-->
    `
})

// 报告大纲（目录树）
const reportOutline = ref([])

// 数据源信息
const dataSource = ref({
  fileName: '',
  pathSegments: [],
  tableName: '',
  fieldName: ''
})

// 数据源树数据
const sourceTreeRef = ref(null)
const selectedDataSourceNode = ref(null)
const sourceTreeData = ref([
  {
    id: 'prod-root-1',
    label: '主产品（合格证号/质控卡号）',
    type: 'product',
    children: [
      {
        id: 'prod-1',
        label: '控制单元组件 (QC-2025-001)',
        type: 'product',
        children: [
          {
            id: 'comp-1-1',
            label: '组件：伺服驱动模块',
            type: 'kit',
            children: [
              {
                id: 'part-1-1-1',
                label: '零件：控制单元 (HG-99)',
                type: 'part',
                children: [
                  {
                    id: 'attach-1-1-1-1',
                    label: '实测附件：电压稳定性测试',
                    type: 'attachment',
                    fileName: 'voltage_stability.xlsx',
                    pathSegments: ['root', 'assembly', 'elec'],
                    tableName: 'T_ELEC_RESULTS',
                    fieldName: 'VOLTAGE_VAL'
                  },
                  {
                    id: 'attach-1-1-1-2',
                    label: '实测附件：绝缘等级评定',
                    type: 'attachment',
                    fileName: 'insulation_rating.pdf',
                    pathSegments: ['root', 'testing', 'safety'],
                    tableName: 'T_SAFETY_CHECK',
                    fieldName: 'INS_DEGREE'
                  }
                ]
              },
              {
                id: 'part-1-1-2',
                label: '零件：感生磁环 (MAG-01)',
                type: 'part',
                children: [
                   {
                    id: 'attach-1-1-2-1',
                    label: '实测附件：磁通量特性数据',
                    type: 'attachment',
                    fileName: 'magnetic_flux_data.docx',
                    pathSegments: ['root', 'qc', 'magnetic'],
                    tableName: 'T_MAGNETIC_DATA',
                    fieldName: 'FLUX_VAL'
                  }
                ]
              }
            ]
          },
          {
            id: 'comp-1-2',
            label: '组件：外壳密封组',
            type: 'kit',
            children: [
               {
                id: 'nest-comp-1-2-1',
                label: '嵌套组件：密封圈支架',
                type: 'kit',
                children: [
                   {
                    id: 'part-1-2-1-1',
                    label: '零件：特制丁腈胶圈',
                    type: 'part',
                    children: [
                       {
                        id: 'attach-1-2-1-1-1',
                        label: '实测附件：气密性实验报告',
                        type: 'attachment',
                        fileName: 'air_leakage_test.pdf',
                        pathSegments: ['root', 'factory', 'air'],
                        tableName: 'T_AIR_CHECK',
                        fieldName: 'PRESSURE_DROP'
                      }
                    ]
                  }
                ]
              }
            ]
          },
           {
            id: 'attach-1-3',
            label: '产品总装实测：外观完整性',
            type: 'attachment',
            fileName: 'assembly_appearance.jpg',
            pathSegments: ['root', 'final'],
            tableName: 'T_FINAL_INSPECTION',
            fieldName: 'APP_STATUS'
          }
        ]
      },
      {
        id: 'prod-2',
        label: '主产品：控制电磁阀 (QC-2025-X02)',
        type: 'product',
        children: [
           {
            id: 'comp-2-1',
            label: '组件：推进系统',
            type: 'kit',
            children: [
               {
                 id: 'part-2-1-1',
                 label: '零件：推力矢量喷管',
                 type: 'part',
                 children: [
                    {
                      id: 'attach-2-1-1-1',
                      label: '实测附件：喷管强度校核',
                      type: 'attachment',
                      fileName: 'nozzle_strength.xlsx',
                      pathSegments: ['root', 'design', 'calc'],
                      tableName: 'T_DESIGN_RESULTS',
                      fieldName: 'STRESS_MAX'
                    }
                 ]
               }
            ]
          }
        ]
      }
    ]
  }
])

// 状态
const loading = ref(true)
const downloading = ref(false)
const downloadProgress = ref(0)
const regenerating = ref(false)
const selectedVariable = ref(null)
const regenerateDialogVisible = ref(false)
const reportContentRef = ref(null)

// ✅ 加载报告数据
const loadReport = async () => {
  console.log('🚀 开始加载报告, reportId:', reportId)
  
  if (!reportId) {
    ElMessage.error('报告ID不存在')
    router.push('/report/history')
    return
  }

  // ✅ 如果是 Mock ID，直接使用初始化的静态数据
  if (reportId === 'IP-001') {
    loading.value = true
    try {
      console.log('📝 使用 Mock 报告数据 (IP-001)')
      // 设置模拟大纲
      reportOutline.value = [
        { id: '1', label: '1. 报告摘要', children: [] },
        { id: '2', label: '2. 产品基本信息', children: [] },
        { id: '3', label: '3. 生产过程质量数据', children: [] },
        { id: '4', label: '4. 检测结果分析', children: [] },
        { id: '5', label: '5. 判定结论', children: [] }
      ]
      reportData.value.outline = reportOutline.value
      
      // 模拟加载延迟
      await new Promise(resolve => setTimeout(resolve, 800))
      
      await nextTick()
      bindDynamicDataEvents()
      console.log('✅ Mock 报告数据加载成功')
      return
    } finally {
      loading.value = false
    }
  }

  loading.value = true
  try {
    console.log('📡 调用 getReportDetail API...')
    const response = await getReportDetail(reportId)
    console.log('✅ API 返回原始数据:', response)
    
    // ✅ 兼容多种数据格式
    const data = response.data || response
    console.log('📦 处理后的数据:', data)
    
    // ✅ 安全地赋值，确保所有字段都存在
    reportData.value = {
      id: data.id || reportId,
      title: data.title || '未命名报告',
      qcNumber: data.qcNumber || '',
      content: data.content || '',
      createdAt: data.createdAt || Date.now(),
      outline: data.outline || []
    }
    
    reportOutline.value = data.outline || []
    
    console.log('✅ 报告数据加载成功')
    console.log('📊 reportData.value:', reportData.value)
    console.log('📊 reportOutline.value:', reportOutline.value)
    
    // ✅ 等待DOM更新后绑定事件
    await nextTick()
    bindDynamicDataEvents()
    
  } catch (error) {
    console.error('❌ 加载报告失败:', error)
    ElMessage.error('加载报告失败: ' + (error.message || '未知错误'))
    
    // 加载失败后清空数据
    reportData.value = {
      id: '',
      title: '',
      qcNumber: '',
      content: '',
      createdAt: '',
      outline: []
    }
  } finally {
    loading.value = false
  }
}

// 绑定动态数据点击事件（监听器已在 handleContentClick 中实现）
const bindDynamicDataEvents = () => {
  // 不再需要手动绑定，使用模板中的 @click
}

// 报告内容点击处理（事件委托）
const handleContentClick = (e) => {
  const target = e.target
  if (target.classList.contains('dynamic-data')) {
    const sourceId = target.dataset.sourceId
    console.log('📊 点击动态数据，sourceId:', sourceId)
    showDataSource(sourceId)
  }
}

// 显示数据源信息
const showDataSource = (sourceId) => {
  console.log('📊 显示数据源信息, sourceId:', sourceId)
  selectedVariable.value = sourceId
  
  // 在树中查找节点
  const findNode = (nodes, id) => {
    for (const node of nodes) {
      if (node.id === id) return node
      if (node.children) {
        const found = findNode(node.children, id)
        if (found) return found
      }
    }
    return null
  }
  
  const node = findNode(sourceTreeData.value, sourceId)
  if (node) {
    selectedDataSourceNode.value = node
    // 自动展开并选中树节点
    nextTick(() => {
      if (sourceTreeRef.value) {
        sourceTreeRef.value.setCurrentKey(sourceId)
        // 滚动到该节点（如果需要）
      }
    })
    
    // 给正文中的对应元素添加临时高亮
    highlightContentData(sourceId)
  }
}

// 树节点点击处理
const handleSourceNodeClick = (data) => {
  if (data.type === 'attachment') {
    selectedDataSourceNode.value = data
    selectedVariable.value = data.id
    highlightContentData(data.id)
  } else {
    selectedDataSourceNode.value = null
  }
}

// 高亮正文中的数据
const highlightContentData = (sourceId) => {
  // 清除之前的高亮
  const prevHighlights = document.querySelectorAll('.highlight-active')
  prevHighlights.forEach(el => el.classList.remove('highlight-active'))
  
  // 添加新的高亮
  const elements = document.querySelectorAll(`[data-source-id="${sourceId}"]`)
  elements.forEach(el => {
    el.classList.add('highlight-active')
    // 只有在点击树节点时才自动滚动正文，如果是点击正文触发的就不需要再滚回去了
    // 但为了简化逻辑，统一处理
    el.scrollIntoView({ behavior: 'smooth', block: 'center' })
  })
}

// 关闭数据源面板
const closeDataSource = () => {
  selectedVariable.value = null
}

// 目录节点点击（滚动到对应章节）
const handleNodeClick = (data) => {
  console.log('📍 点击目录节点:', data)
  const element = document.getElementById(`section-${data.id}`)
  if (element) {
    element.scrollIntoView({ behavior: 'smooth', block: 'start' })
  } else {
    console.warn('⚠️ 未找到对应章节元素')
  }
}

// ✅ 下载报告
const handleDownload = async () => {
  if (!reportData.value.id) {
    ElMessage.warning('报告数据未加载完成')
    return
  }

  downloading.value = true
  downloadProgress.value = 0
  
  try {
    console.log('📥 开始下载报告:', reportData.value.id)
    
    const response = await downloadReport(reportData.value.id, {
      onDownloadProgress: (progressEvent) => {
        if (progressEvent.total) {
          downloadProgress.value = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          )
          console.log('📊 下载进度:', downloadProgress.value + '%')
        }
      }
    })
    
    // ✅ 兼容不同的响应格式
    const blob = response.data instanceof Blob 
      ? response.data 
      : new Blob([response.data], { 
          type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' 
        })
    
    // 创建下载链接
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    
    // 生成文件名
    const timestamp = new Date().getTime()
    const filename = `${reportData.value.title || '报告'}_${timestamp}.docx`
    link.download = filename
    
    // 触发下载
    document.body.appendChild(link)
    link.click()
    
    // 清理
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    
    ElMessage.success('下载成功')
    console.log('✅ 下载完成:', filename)
    
    downloadProgress.value = 100
    
    // 2秒后重置进度
    setTimeout(() => {
      downloadProgress.value = 0
    }, 2000)
    
  } catch (error) {
    console.error('❌ 下载失败:', error)
    ElMessage.error('下载失败，请稍后重试')
    downloadProgress.value = 0
  } finally {
    downloading.value = false
  }
}

// 显示重新生成对话框
const showRegenerateDialog = () => {
  regenerateDialogVisible.value = true
}

// ✅ 重新生成报告
const handleRegenerate = async () => {
  regenerating.value = true
  try {
    console.log('🔄 重新生成报告:', reportData.value.id)
    const response = await regenerateReport(reportData.value.id)
    
    ElMessage.success('已提交重新生成请求')
    console.log('✅ 重新生成请求成功:', response)
    
    regenerateDialogVisible.value = false
    
    // 跳转回生成页面
    router.push({
      path: '/report/generate',
      query: { qcNumber: reportData.value.qcNumber }
    })
  } catch (error) {
    console.error('❌ 重新生成失败:', error)
    ElMessage.error('重新生成失败: ' + (error.message || '未知错误'))
  } finally {
    regenerating.value = false
  }
}

// 关闭预览
const handleClose = () => {
  console.log('🚪 关闭预览')
  emit('close')
  if (!props.id) {
    router.push('/report/history')
  }
}

// ✅ 格式化日期
const formatDate = (timestamp) => {
  if (!timestamp) return '--'
  
  try {
    const date = new Date(timestamp)
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    })
  } catch (error) {
    console.error('日期格式化失败:', error)
    return '--'
  }
}

// 页面加载时获取报告数据
onMounted(() => {
  loadReport()
})
</script>

<style scoped lang="scss">
.report-preview-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #F5F7FA;
  overflow: hidden;

  // 顶部导航栏
  .page-header {
    height: 60px;
    flex-shrink: 0;
    background: var(--primary-blue);
    color: #fff;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 24px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    z-index: 100;
  }

  // ✅ 加载状态
  .loading-container {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 16px;
    min-height: 400px;

    .el-icon {
      color: var(--el-color-primary);
    }

    p {
      font-size: 14px;
      color: #8C8C8C;
    }
  }

  // ✅ 错误状态
  .error-container {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 400px;
  }

  // 报告操作栏
  .report-actions {
    background: #fff;
    padding: 20px 24px;
    border-bottom: 1px solid #E8E8E8;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-shrink: 0;
    z-index: 90;

    .report-title {
      flex: 1;

      h2 {
        font-size: 18px;
        font-weight: 600;
        margin: 0 0 8px 0;
        color: #262626;
      }

      .report-meta {
        display: flex;
        align-items: center;
        gap: 12px;

        .create-time {
          font-size: 14px;
          color: #8C8C8C;
        }
      }
    }

    .action-buttons {
      display: flex;
      gap: 12px;
    }
  }

  // 主容器
  .main-container {
    display: flex;
    flex: 1;
    overflow: hidden;
    min-height: 0;
  }

  // 左侧栏
  .left-sidebar {
    width: 240px;
    flex-shrink: 0;
    background: #FAFAFA;
    border-right: 1px solid #E8E8E8;
    overflow-y: auto;

    .sidebar-header {
      padding: 16px;
      border-bottom: 1px solid #E8E8E8;

      h3 {
        font-size: 16px;
        font-weight: 600;
        margin: 0;
      }
    }

    .tree-node {
      display: flex;
      align-items: center;
      gap: 8px;
    }
  }

  // 中间内容区
  .content-area {
    flex: 1;
    background: #fff;
    overflow-y: auto;
    padding: 24px 40px;

    &.no-sidebar {
      margin-left: 0;
    }

    .report-content {
      max-width: 900px;
      margin: 0 auto;
      font-size: 14px;
      line-height: 1.8;

      // 报告标题样式
      :deep(h1) {
        font-size: 28px;
        font-weight: 600;
        margin: 0 0 24px 0;
        text-align: center;
      }

      :deep(h2) {
        font-size: 22px;
        font-weight: 600;
        margin: 32px 0 16px 0;
        border-bottom: 2px solid var(--primary-blue);
        padding-bottom: 8px;
      }

      // 报告内容 body 样
      .report-content-body {
        width: 100%;
        overflow-x: auto;
        box-sizing: border-box !important;
        
        * {
          box-sizing: border-box !important;
        }
        
        // 允许 Word 导出的 Section 容器保留其原有的布局逻辑，但防止过度溢出
        :deep(.Section0) {
          width: auto;
          max-width: 100%;
        }
      }

      :deep(h1) {
        font-size: 24px;
        font-weight: 600;
        margin: 32px 0 16px 0;
        text-align: center;
      }

      :deep(h2) {
        font-size: 20px;
        font-weight: 600;
        margin: 28px 0 14px 0;
        border-bottom: 2px solid #F0F0F0;
        padding-bottom: 8px;
      }

      :deep(h3) {
        font-size: 18px;
        font-weight: 500;
        margin: 24px 0 12px 0;
      }

      // 动态数据样式
      :deep(.dynamic-data) {
        color: var(--primary-blue);
        font-weight: 500;
        cursor: pointer;
        text-decoration: underline;
        text-decoration-style: dotted;
        transition: all 0.2s;

        &:hover {
          background: rgba(0, 80, 179, 0.1);
          padding: 2px 4px;
          border-radius: 2px;
        }
      }

      // 表格样式
      :deep(table) {
        width: 100% !important; 
        max-width: 100% !important;
        table-layout: auto !important; 
        border-collapse: collapse;
        margin: 16px 0 !important;
        border: 1px solid #E8E8E8 !important;
        margin-left: 0 !important; 
        margin-right: 0 !important;
        box-sizing: border-box !important;

        th, td {
          border: 1px solid #E8E8E8 !important;
          padding: 8px 12px !important;
          word-break: normal !important; 
          overflow-wrap: break-word !important; 
          white-space: normal !important;
          height: auto !important; 
          text-align: center !important;
        }

        tr {
          height: auto !important;
        }

        th {
          background: #FAFAFA;
          font-weight: 600;
        }
      }

      // 修复文字重叠问题
      :deep(p) {
        line-height: 1.6 !important; // 统一行高
        margin: 8px 0 !important; // 统一间距
        height: auto !important;
        overflow: visible !important;
      }

      :deep(span) {
        line-height: inherit !important;
      }

      // 产品编号高亮
      :deep(.product-number-blue) {
        color: #0050b3;
        font-weight: 500;
      }
    }
  }

  // 右侧栏
  .right-sidebar {
    width: 320px;
    flex-shrink: 0;
    background: #FAFAFA;
    border-left: 1px solid #E8E8E8;
    display: flex;
    flex-direction: column;
    z-index: 100;

    .sidebar-header {
      padding: 16px;
      background: #fff;
      border-bottom: 1px solid #E8E8E8;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-shrink: 0;

      h3 {
        font-size: 15px;
        font-weight: 600;
        margin: 0;
        color: #262626;
      }

      .close-icon {
        cursor: pointer;
        padding: 4px;
        border-radius: 4px;
        &:hover {
          background: #f0f0f0;
          color: var(--primary-blue);
        }
      }
    }

    .data-source-tree-container {
      flex: 1;
      overflow-y: auto;
      padding: 12px;

      :deep(.el-tree) {
        background: transparent;
        .el-tree-node__content {
          height: auto;
          padding: 6px 0;
        }
      }

      .custom-tree-node {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 13px;
        white-space: normal;
        line-height: 1.4;

        .el-icon {
          flex-shrink: 0;
          color: #8c8c8c;
        }

        .node-label {
          color: #595959;
        }
      }

      :deep(.is-current) {
        .node-label {
          color: var(--primary-blue);
          font-weight: 600;
        }
        .el-icon {
          color: var(--primary-blue);
        }
      }
    }

    .data-source-detail {
      background: #fff;
      border-top: 1px solid #E8E8E8;
      padding: 20px;
      flex-shrink: 0;
      box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.05);

      h4 {
        margin: 0 0 16px 0;
        font-size: 14px;
        color: #262626;
        border-left: 3px solid var(--primary-blue);
        padding-left: 8px;
      }

      .detail-item {
        margin-bottom: 12px;

        .label {
          font-size: 12px;
          color: #8C8C8C;
          margin-bottom: 4px;
        }

        .value {
          font-size: 13px;
          color: #262626;
          word-break: break-all;
          line-height: 1.5;

          &.code-font {
            font-family: 'Courier New', Courier, monospace;
            background: #f5f5f5;
            padding: 2px 6px;
            border-radius: 4px;
          }
        }
      }
    }
  }

  // 高亮样式
  :deep(.dynamic-data) {
    &.highlight-active {
      background: rgba(255, 255, 0, 0.3) !important;
      outline: 2px solid #ffd666;
      border-radius: 2px;
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
      box-shadow: 0 0 8px rgba(255, 214, 102, 0.5);
    }
  }
}

.fade-enter-active, .fade-leave-active {
  transition: opacity 0.3s, transform 0.3s;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
  transform: translateY(10px);
}
</style>
