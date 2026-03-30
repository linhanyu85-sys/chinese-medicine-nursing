#!/usr/bin/env bash
set -euo pipefail

# 独立部署参数（不影响已存在项目）
REPO_URL="${REPO_URL:-https://github.com/linhanyu85-sys/chinese-medicine-nursing.git}"
REPO_BRANCH="${REPO_BRANCH:-main}"
INSTALL_ROOT="${INSTALL_ROOT:-/opt/tcm-knowledge-nursing}"
SERVICE_NAME="${SERVICE_NAME:-tcm-knowledge-backend}"
ENV_FILE="${ENV_FILE:-/etc/tcm-knowledge-backend.env}"
APP_PORT="${APP_PORT:-18791}"
RUN_USER="${RUN_USER:-ubuntu}"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "请用 root 运行本脚本（sudo bash deploy_backend.sh）"
  exit 1
fi

echo "[1/8] 安装系统依赖..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y git python3 python3-venv python3-pip curl

echo "[2/8] 拉取项目代码到独立目录: ${INSTALL_ROOT}"
mkdir -p "${INSTALL_ROOT}"
if [[ -d "${INSTALL_ROOT}/.git" ]]; then
  git -C "${INSTALL_ROOT}" fetch --all --prune
  git -C "${INSTALL_ROOT}" checkout "${REPO_BRANCH}"
  git -C "${INSTALL_ROOT}" pull --ff-only origin "${REPO_BRANCH}"
else
  git clone -b "${REPO_BRANCH}" "${REPO_URL}" "${INSTALL_ROOT}"
fi

PROJECT_ROOT=""
if [[ -d "${INSTALL_ROOT}/backend" && -d "${INSTALL_ROOT}/deploy/aliyun" ]]; then
  PROJECT_ROOT="${INSTALL_ROOT}"
elif [[ -d "${INSTALL_ROOT}/stitch/backend" && -d "${INSTALL_ROOT}/stitch/deploy/aliyun" ]]; then
  PROJECT_ROOT="${INSTALL_ROOT}/stitch"
else
  echo "部署失败：未找到项目目录。"
  echo "已检查："
  echo "  - ${INSTALL_ROOT}/backend"
  echo "  - ${INSTALL_ROOT}/stitch/backend"
  exit 1
fi

APP_ROOT="${PROJECT_ROOT}/backend"
DEPLOY_ROOT="${PROJECT_ROOT}/deploy/aliyun"

echo "[3/8] 创建 Python 虚拟环境..."
python3 -m venv "${APP_ROOT}/.venv"

echo "[4/8] 安装 Python 依赖..."
"${APP_ROOT}/.venv/bin/pip" install --upgrade pip
"${APP_ROOT}/.venv/bin/pip" install -r "${APP_ROOT}/requirements.txt"

echo "[5/8] 准备后端环境变量文件..."
if [[ ! -f "${ENV_FILE}" ]]; then
  cp "${DEPLOY_ROOT}/tcm_knowledge_backend.env.example" "${ENV_FILE}"
  sed -i "s/APP_PORT=.*/APP_PORT=${APP_PORT}/" "${ENV_FILE}"
  echo ""
  echo "已创建 ${ENV_FILE}，请先编辑 ALIYUN_API_KEY 后再重启服务。"
fi

echo "[6/8] 写入 systemd 服务..."
SERVICE_PATH="/etc/systemd/system/${SERVICE_NAME}.service"
cp "${DEPLOY_ROOT}/tcm-knowledge-backend.service" "${SERVICE_PATH}"
sed -i "s#^User=.*#User=${RUN_USER}#" "${SERVICE_PATH}"
sed -i "s#^WorkingDirectory=.*#WorkingDirectory=${APP_ROOT}#" "${SERVICE_PATH}"
sed -i "s#^EnvironmentFile=.*#EnvironmentFile=${ENV_FILE}#" "${SERVICE_PATH}"
sed -i "s#^ExecStart=.*#ExecStart=${APP_ROOT}/.venv/bin/python ${APP_ROOT}/server.py#" "${SERVICE_PATH}"

echo "[7/8] 启动服务..."
systemctl daemon-reload
systemctl enable "${SERVICE_NAME}"
systemctl restart "${SERVICE_NAME}"

echo "[8/8] 状态检查..."
systemctl --no-pager --full status "${SERVICE_NAME}" || true
sleep 1
curl -fsS "http://127.0.0.1:${APP_PORT}/api/health" || true

echo ""
echo "部署完成。"
echo "服务名: ${SERVICE_NAME}"
echo "后端地址: http://<你的ECS公网IP>:${APP_PORT}"
echo "如果外网不可访问，请在阿里云安全组放行 TCP ${APP_PORT}。"
