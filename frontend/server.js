import express from 'express';
import { createServer as createViteServer } from 'vite';
import path from 'path';
import { fileURLToPath } from 'url';
import cors from 'cors';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function startServer() {
  const app = express();
  const PORT = 3000;

  app.use(cors());
  app.use(express.json());

  // --- Mock API Endpoints ---

  app.post('/api/upload/file', (req, res) => {
    // Simple mock upload response
    res.json({
      code: 200,
      data: {
        file_path: 'mock/path/quality_data.xlsx',
        total_records: 156,
        records: [
          { 日期: '2026-05-01', 产品编号: 'P001', 检测项: '外径', 标准值: '10.00±0.05', 实测值: '10.02', 判定: '合格', 操作员: '张伟' },
          { 日期: '2026-05-01', 产品编号: 'P002', 检测项: '外径', 标准值: '10.00±0.05', 实测值: '10.08', 判定: '不合格', 操作员: '张伟' },
          { 日期: '2026-05-02', 产品编号: 'P003', 检测项: '外径', 标准值: '10.00±0.05', 实测值: '10.01', 判定: '合格', 操作员: '李四' },
          { 日期: '2026-05-02', 产品编号: 'P004', 检测项: '外径', 标准值: '10.00±0.05', 实测值: '9.98', 判定: '合格', 操作员: '李四' },
          { 日期: '2026-05-03', 产品编号: 'P005', 检测项: '外径', 标准值: '10.00±0.05', 实测值: '10.05', 判定: '合格', 操作员: '王强' },
        ]
      }
    });
  });

  app.post('/api/diagnosis/analyze', (req, res) => {
    res.json({
      code: 200,
      data: {
        quality_trend: {
          dates: ['05-01', '05-02', '05-03', '05-04', '05-05', '05-06', '05-07'],
          rates: [98.5, 96.2, 94.8, 92.1, 89.5, 88.2, 88.0]
        },
        root_causes: [
          {
            rank: 1,
            cause: '3号精密磨床主轴轴承磨损',
            category: '设备',
            confidence: 0.92,
            impact: '导致加工件径向跳动超差，合格率下降8%',
            evidence: [
              '三次元检测数据波动呈现明显的周期性特征',
              '近期设备维护记录显示主轴振动值超标15%',
              '该问题在高速加工模式下尤为显著'
            ],
            impact: '严重影响精密件加工进度'
          },
          {
            rank: 2,
            cause: '切削液浓度不达标',
            category: '环境',
            confidence: 0.78,
            impact: '散热不良导致工件热变形',
            evidence: [
              '测量数据在下午高温时段偏差增大',
              '车间环境温度近期波动较大'
            ],
            impact: '导致工件表面粗糙度不稳定'
          }
        ],
        similar_cases: [
          {
            case_id: 'QC-2025-008',
            title: '主轴轴承损坏导致的外径尺寸超差案例',
            similarity: 0.95,
            solution: '更换主轴高精度轴承，校准同轴度'
          },
          {
            case_id: 'QC-2024-112',
            title: '冷却系统故障引发的批量质量波动',
            similarity: 0.72,
            solution: '清理冷却管路，更换高品质切削液'
          }
        ]
      }
    });
  });

  app.post('/api/solution/generate', (req, res) => {
    res.json({
      code: 200,
      data: {
        solutions: [
          {
            priority: 'P0-紧急',
            action: '停机更换3号磨床主轴轴承',
            responsible: '设备运维部',
            estimated_cost: 4500,
            expected_effect: '彻底解决轴向跳动，预计合格率回升至99%以上',
            implementation_time: '24小时内',
            roi: '高'
          },
          {
            priority: 'P1-重要',
            action: '调整切削液配比并安装实时监控计',
            responsible: '生产技术部',
            estimated_cost: 1200,
            expected_effect: '稳定加工温度，减少工件热变形风险',
            implementation_time: '3个工作日',
            roi: '中'
          },
          {
            priority: 'P2-一般',
            action: '对夜班操作员加强过程检测培训',
            responsible: '质量管理部',
            estimated_cost: 500,
            expected_effect: '降低人为操作不规范导致的微小偏差',
            implementation_time: '一周内',
            roi: '低'
          }
        ]
      }
    });
  });

  // --- Vite Integration ---

  if (process.env.NODE_ENV !== 'production') {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  } else {
    // Production serving
    const distPath = path.join(__dirname, 'dist');
    app.use(express.static(distPath));
    app.get('/{*path}', (req, res) => {
      res.sendFile(path.join(distPath, 'index.html'));
    });
  }

  app.listen(PORT, '0.0.0.0', () => {
    console.log(`Server running at http://localhost:${PORT}`);
  });
}

startServer();
