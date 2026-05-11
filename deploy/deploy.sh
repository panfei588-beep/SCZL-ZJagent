#!/bin/bash
set -e

echo "=========================================="
echo "  质量异常诊断系统 - 一键部署脚本"
echo "=========================================="

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo "[ERROR] 未检测到 Docker，请先安装 Docker"
    exit 1
fi

if ! docker compose version &> /dev/null && ! command -v docker-compose &> /dev/null; then
    echo "[ERROR] 未检测到 Docker Compose，请先安装"
    exit 1
fi

# 兼容新旧版 docker compose 命令
DC="docker compose"
if ! docker compose version &> /dev/null; then
    DC="docker-compose"
fi

# 检查 .env 文件
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "[WARN] 已生成 .env 文件，请填入 DASHSCOPE_API_KEY 后重新运行："
    echo "       vim .env"
    exit 1
fi

if grep -q "your_dashscope_api_key_here" .env; then
    echo "[WARN] 请先在 .env 文件中配置 DASHSCOPE_API_KEY"
    echo "       获取地址: https://dashscope.aliyun.com/"
    exit 1
fi

echo "[1/5] 构建 Docker 镜像..."
$DC build

echo "[2/5] 启动基础依赖（etcd、minio、postgres）..."
$DC up -d etcd minio postgres

echo "      等待 PostgreSQL 就绪..."
until $DC exec -T postgres pg_isready -U postgres &> /dev/null; do
    sleep 2
done
echo "      PostgreSQL 已就绪"

echo "[3/5] 启动 Milvus..."
$DC up -d milvus

echo "      等待 Milvus 就绪..."
until curl -sf http://localhost:9091/healthz &> /dev/null; do
    sleep 5
done
echo "      Milvus 已就绪"

echo "[4/5] 启动后端服务..."
$DC up -d backend

echo "      等待后端就绪..."
until curl -sf http://localhost:8000/api/health &> /dev/null; do
    sleep 3
done
echo "      后端已就绪"

echo "[5/5] 启动前端服务..."
$DC up -d frontend

# 获取服务器 IP
SERVER_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")

echo ""
echo "=========================================="
echo "  部署完成！"
echo "=========================================="
echo ""
echo "  访问地址:    http://${SERVER_IP}"
echo "  API 文档:    http://${SERVER_IP}:8000/docs"
echo ""
echo "  首次部署需初始化知识库："
echo "  docker exec quality-backend python data/init_knowledge_base.py"
echo ""
echo "  查看日志："
echo "  $DC logs -f backend"
echo "  $DC logs -f frontend"
echo ""
