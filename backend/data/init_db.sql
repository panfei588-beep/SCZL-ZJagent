-- 航天运载火箭质量异常诊断系统 - 数据库初始化脚本

-- 诊断历史表
CREATE TABLE IF NOT EXISTS diagnosis_history (
    id          SERIAL PRIMARY KEY,
    file_name   VARCHAR(255),
    file_path   VARCHAR(500),
    equipment   VARCHAR(100),
    days        INTEGER,
    operator    VARCHAR(100),
    created_at  TIMESTAMP DEFAULT NOW(),
    result      JSONB
);

-- 改进方案表
CREATE TABLE IF NOT EXISTS improvement_solutions (
    id              SERIAL PRIMARY KEY,
    diagnosis_id    INTEGER REFERENCES diagnosis_history(id) ON DELETE CASCADE,
    priority        VARCHAR(20),
    action          TEXT,
    responsible     VARCHAR(100),
    estimated_cost  INTEGER,
    expected_effect TEXT,
    implementation_time VARCHAR(50),
    roi             TEXT,
    status          VARCHAR(20) DEFAULT 'pending',  -- pending / in_progress / done
    created_at      TIMESTAMP DEFAULT NOW()
);

-- 工单表
CREATE TABLE IF NOT EXISTS work_orders (
    id              SERIAL PRIMARY KEY,
    order_no        VARCHAR(50) UNIQUE,
    solution_id     INTEGER REFERENCES improvement_solutions(id) ON DELETE SET NULL,
    title           TEXT,
    description     TEXT,
    assignee        VARCHAR(100),
    status          VARCHAR(20) DEFAULT 'open',     -- open / in_progress / closed
    created_at      TIMESTAMP DEFAULT NOW(),
    closed_at       TIMESTAMP
);

-- 质量记录表（存储上传的检测数据）
CREATE TABLE IF NOT EXISTS quality_records (
    id              SERIAL PRIMARY KEY,
    diagnosis_id    INTEGER REFERENCES diagnosis_history(id) ON DELETE CASCADE,
    record_date     DATE,
    product_no      VARCHAR(100),
    inspection_item VARCHAR(100),
    standard_value  VARCHAR(50),
    measured_value  NUMERIC(12, 4),
    deviation       NUMERIC(12, 4),
    result          VARCHAR(20),
    equipment       VARCHAR(100),
    operator        VARCHAR(100),
    shift           VARCHAR(20),
    created_at      TIMESTAMP DEFAULT NOW()
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_diagnosis_created_at ON diagnosis_history(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_quality_records_diagnosis ON quality_records(diagnosis_id);
CREATE INDEX IF NOT EXISTS idx_quality_records_date ON quality_records(record_date);
CREATE INDEX IF NOT EXISTS idx_solutions_diagnosis ON improvement_solutions(diagnosis_id);
CREATE INDEX IF NOT EXISTS idx_work_orders_status ON work_orders(status);
