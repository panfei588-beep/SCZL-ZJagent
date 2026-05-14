// Mock API for quality reports
export const getReportDetail = async (id) => {
  console.log('Mock: Fetching report detail for', id);
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve({
        id: id,
        title: '增压电磁阀产品生产质量报告',
        qcNumber: 'QC-2026-0513',
        createdAt: new Date().toISOString(),
        content: `
          <h1>增压电磁阀产品生产质量报告</h1>
          <p>本报告针对批次 13JPSBG-2025194 的增压电磁阀产品进行了深度质量解析。</p>
          <h2>1. 综述</h2>
          <p>经过 AI 诊断分析，当前批次产品在阻值一致性方面表现良好，但发现在极端温升情况下存在微小的响应迟滞风险。</p>
          <h2>2. 检测数据可视化</h2>
          <table>
            <thead>
              <tr><th>检测项</th><th>均值</th><th>标准差</th><th>判定</th></tr>
            </thead>
            <tbody>
              <tr><td>阻值-1和2</td><td>25.43</td><td>0.12</td><td>合格</td></tr>
              <tr><td>阻值-3和4</td><td>25.51</td><td>0.14</td><td>合格</td></tr>
              <tr><td>阻值-1和3</td><td>25.38</td><td>0.11</td><td>合格</td></tr>
            </tbody>
          </table>
          <h2>3. 改进建议</h2>
          <p>建议调整工艺参数，优化温漂补偿算法字段 <span class="dynamic-data" data-source-id="VAR_001">temperature_compensation</span>。</p>
        `,
        outline: [
          { id: '1', label: '1. 综述' },
          { id: '2', label: '2. 检测数据可视化' },
          { id: '3', label: '3. 改进建议' }
        ]
      });
    }, 500);
  });
};

export const downloadReport = async (id) => {
  console.log('Mock: Downloading report', id);
  return { data: new Blob(['Mock data'], { type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' }) };
};

export const regenerateReport = async (id) => {
  console.log('Mock: Regenerating report', id);
  return { code: 200, message: 'Success' };
};

export const getDataSourceInfo = async (sourceId) => {
  console.log('Mock: Fetching data source for', sourceId);
  return {
    fileName: 'Quality_Data_Log_V2.xlsx',
    pathSegments: ['root', 'archive', 'manufacturing', 'line_A'],
    tableName: 'VALVE_TEST_RESULTS',
    fieldName: 'TEMP_COMP_FACTOR'
  };
};
