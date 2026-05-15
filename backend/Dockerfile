FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖（MinerU 需要 + matplotlib CJK 字体 + weasyprint PDF 生成需要）
# 切换 apt 源为阿里云镜像（国内服务器加速）
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || \
    sed -i 's|http://deb.debian.org|http://mirrors.aliyun.com|g' /etc/apt/sources.list
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    fonts-noto-cjk \
    wget \
    libpango-1.0-0 \
    libharfbuzz-subset0 \
    libpangoft2-1.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --timeout 300 -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/

# 下载 MinerU 模型（pipeline 模式，失败不阻断构建）
RUN python -m mineru.tools.download_models --backend pipeline 2>/dev/null; echo "MinerU model download done"

COPY . .

RUN mkdir -p uploads

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
