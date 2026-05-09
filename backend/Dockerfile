FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖（MinerU 需要）
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    wget \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/

# 下载 MinerU 模型（pipeline 模式，失败不阻断构建）
RUN python -m mineru.tools.download_models --backend pipeline 2>/dev/null; echo "MinerU model download done"

COPY . .

RUN mkdir -p uploads

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
