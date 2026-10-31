# CorpClaw — 智能制造质量异常诊断数字员工

AI 驱动的质量异常诊断系统，面向智能制造制造质检场景，实现质量数据自动解析、6 维根因分析、改进方案生成全流程智能化。

---

## 功能特性

- **多格式文件解析** — 支持 Excel / PDF / 图片 / Word，MinerU OCR 引擎
- **LangGraph 6 节点工作流** — 数据分析 → 校验 → 诊断 → 校验 → 决策 → 输出整合
- **双知识库 RAG 检索** — 诊断知识库 + 改善知识库，Milvus 向量相似度匹配
- **6 维根因分析** — 人 / 机 / 料 / 法 / 环 / 测，含置信度评分与证据链
- **数据校验与重试** — 字段完整性 / 数值范围 / 时间连续性校验，最多 3 次回退
- **置信度评估** — 低于 0.6 自动打标警告，不阻断流程
- **matplotlib 图表生成** — 合格率趋势图（含包络线）+ 数据分布图
- **改进方案自动生成** — 含优先级 / 责任部门 / 预估成本 / ROI

---

## 技术栈

| 层次 | 技术 |
|------|------|
| 前端 | Vue 3 + Element Plus + ECharts |
| 后端 | FastAPI (Python 3.11) |
| 工作流编排 | LangGraph StateGraph |
| 大模型 | Qwen-Max (DashScope) |
| 向量库 | Milvus v2.4 |
| 文件解析 | MinerU 3.1+ |
| 图表生成 | matplotlib |
| 部署 | Docker Compose |

---

## 快速开始

### 前置条件

- Docker 20.10+ / Docker Compose 2.0+
- DashScope API Key（[申请](https://dashscope.aliyun.com/)）

### 部署

```bash
# 1. 克隆项目
git clone https://github.com/lukesun1987/digitalemployee.git
cd digitalemployee/deploy

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填入 DASHSCOPE_API_KEY

# 3. 构建并启动
docker compose up -d --build

# 4. 初始化知识库（首次部署）
docker exec quality-backend python data/init_knowledge_base.py
```

启动后访问 `http://localhost` 即可使用前端界面。

### 本地开发

```bash
# 后端
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# 前端
cd frontend
npm install
npm run dev
```

---

## 项目结构

```
├── backend/
│   ├── main.py                    # FastAPI 入口
│   ├── agents/orchestrator.py     # LangGraph StateGraph（6 节点编排）
│   ├── agents/tools.py            # 工具集（向后兼容）
│   ├── services/file_parser.py    # MinerU 文件解析
│   ├── services/chart_generator.py # matplotlib 图表生成
│   ├── knowledge_base/milvus_client.py  # Milvus 双知识库
│   ├── api/                       # REST 接口
│   └── data/cases/                # 预置质量案例
├── frontend/
│   └── src/views/
│       ├── DigitalEmployeeSkills.vue  # 技能卡片
│       └── QualityDiagnosisWorkbench.vue  # 诊断工作台
└── deploy/
    ├── docker-compose.yml         # 完整服务编排
    └── deploy.sh                  # 一键部署脚本
```

---

## API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/upload/file` | POST | 上传质量数据文件 |
| `/api/diagnosis/analyze` | POST | 执行完整诊断工作流 |
| `/api/solution/generate` | POST | 生成改进方案（向后兼容） |

详细参数和返回格式见 [docs/技术文档.md](docs/技术文档.md)

---

## 工作流架构

```
START → data_agent → validate_data
          ↕ 条件边(重试≤3次)
   → diagnosis_agent → validate_diagnosis
          ↕ 低置信打标(不阻断)
   → decision_agent → output_merger → END
```

6 个节点职责：
1. **data_agent** — 解析文件 → 统计计算(max/min/mean/std/包络线) → 生成图表
2. **validate_data** — 数据校验，失败回退重试
3. **diagnosis_agent** — RAG 检索诊断知识库 → Qwen 6维根因分析
4. **validate_diagnosis** — 置信度 > 0.6 检查，低置信打标
5. **decision_agent** — RAG 检索改善知识库 → 生成改进方案
6. **output_merger** — 汇总统计 + 诊断 + 方案 + 图表

---

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DASHSCOPE_API_KEY` | Qwen API Key（必填） | — |
| `MILVUS_HOST` | Milvus 地址 | `milvus-standalone` |
| `MILVUS_PORT` | Milvus 端口 | `19530` |
| `UPLOAD_DIR` | 上传文件目录 | `/app/uploads` |
| `MAX_UPLOAD_SIZE` | 最大上传大小 | `52428800` (50MB) |

---

## 贡献指南

1. 从 `dev` 分支创建特性分支
2. 提交代码并推送到 GitHub
3. 发起 Pull Request 到 `dev`
4. 合并后部署到生产环境

---

## License

MIT
