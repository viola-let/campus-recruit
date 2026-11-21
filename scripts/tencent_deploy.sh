#!/usr/bin/env bash
# CampusRecruit 腾讯云轻量服务器一键部署脚本
# 用法（在腾讯云网页终端以 root 执行）：
#   sudo bash /opt/campus-recruit/scripts/tencent_deploy.sh
# 重复执行即为更新：拉取最新代码、重新构建并重启容器，数据保留在 /opt/campus-data。

set -euo pipefail

APP_DIR="/opt/campus-recruit"
DATA_DIR="/opt/campus-data"
UPLOAD_DIR="/opt/campus-uploads"
REPO_URL="https://github.com/viola-let/campus-recruit.git"
IMAGE="campus-recruit:latest"
CONTAINER="campus-recruit"
PORT="7860"

if [ "$(id -u)" -ne 0 ]; then
  echo "[错误] 请使用 root 执行：sudo bash $0"
  exit 1
fi

echo "[1/6] 安装基础工具"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y git curl ca-certificates unzip

echo "[2/6] 安装并配置 Docker"
if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sh || apt-get install -y docker.io
fi
systemctl enable --now docker

# 腾讯云内网镜像加速（拉取 python:3.12-slim 更快）
mkdir -p /etc/docker
if [ ! -f /etc/docker/daemon.json ]; then
  echo '{"registry-mirrors":["https://mirror.ccs.tencentyun.com"]}' > /etc/docker/daemon.json
  systemctl restart docker
fi

echo "[3/6] 获取项目代码"
if [ -d "$APP_DIR/.git" ]; then
  git -C "$APP_DIR" pull --ff-only
else
  rm -rf "$APP_DIR"
  git clone --depth 1 "$REPO_URL" "$APP_DIR"
fi

# 远端若缺少 Dockerfile（推送未完成时），本地补一份，保证部署可继续
if [ ! -f "$APP_DIR/Dockerfile" ]; then
  cat > "$APP_DIR/Dockerfile" <<'DOCKER'
FROM python:3.12-slim
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user PATH=/home/user/.local/bin:$PATH PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR $HOME/app
COPY --chown=user . $HOME/app
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt
EXPOSE 7860
CMD ["sh", "-c", "streamlit run deploy_app.py --server.port=${PORT:-7860} --server.address=0.0.0.0 --server.headless=true"]
DOCKER
fi

echo "[4/6] 准备持久化目录"
mkdir -p "$DATA_DIR" "$UPLOAD_DIR"
chown -R 1000:1000 "$DATA_DIR" "$UPLOAD_DIR"

echo "[5/6] 构建镜像（首次约 2-5 分钟）"
docker build -t "$IMAGE" "$APP_DIR"

echo "[6/6] 启动容器"
docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
docker run -d \
  --name "$CONTAINER" \
  --restart unless-stopped \
  -p "${PORT}:7860" \
  -e PORT=7860 \
  -v "$DATA_DIR:/home/user/app/data" \
  -v "$UPLOAD_DIR:/home/user/app/uploads" \
  "$IMAGE"

sleep 5
docker ps --filter "name=$CONTAINER"
if curl -fsS -m 10 -o /dev/null "http://127.0.0.1:${PORT}"; then
  IP="$(hostname -I | awk '{print $1}')"
  echo ""
  echo "部署成功：http://${IP}:${PORT}"
  echo "演示账号：student01@seed.campus / Student123!"
  echo "更新代码：重新执行本脚本即可（数据保留）。"
else
  echo "[警告] 容器已启动但页面暂未响应，请执行：docker logs -f ${CONTAINER}"
fi
