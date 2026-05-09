#!/bin/bash
# 航天运载火箭质量异常诊断系统 - 一键部署脚本

set -e

echo "=========================================="
echo "  航天运载火箭质量异常诊断系统 部署脚本"
echo "=========================================="

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo "[ERROR] 未检测到 Docker，请先安装 Docker"
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "[ERROR] 未检测到 Docker Compose，请先安装"
    exit 1
fi

# 检查 .env 文件
if [ ! -f ".env" ]; then
    cp .env.example .env 2>/dev/null || echo "DASHSCOPE_API_KEY=your_key_here" > .env
    echo "[WARN] 请编辑 .env 文件，填入 DASHSCOPE_API_KEY"
    echo "       vim .env"
    exit 1
fi

# 检查 API Key 是否已配置
if grep -q "your_dashscope_api_key_here" .env; then
    echo "[WARN] 请先在 .env 文件中配置 DASHSCOPE_API_KEY"
    echo "       获取地址: https://dashscope.aliyun.com/"
    exit 1
fi

echo "[1/4] 构建 Docker 镜像..."
docker compose build --no-cache

echo "[2/4] 启动基础服务（Milvus + PostgreSQL）..."
docker compose up -d etcd minio postgres
echo "      等待服务就绪..."
sleep 30

echo "[3/4] 启动后端服务..."
docker compose up -d milvus
sleep 20
docker compose up -d backend

echo "[4/4] 启动前端服务..."
docker compose up -d frontend

echo ""
echo "=========================================="
echo "  部署完成！"
echo "=========================================="
echo ""
echo "  前端访问地址: http://$(hostname -I | awk '{print $1}')"
echo "  后端 API 文档: http://$(hostname -I | awk '{print $1}'):8000/docs"
echo ""
echo "  初始化知识库（首次部署需要执行）："
echo "  docker exec quality-backend python data/init_knowledge_base.py"
echo ""
echo "  查看日志："
echo "  docker compose logs -f backend"
echo ""
