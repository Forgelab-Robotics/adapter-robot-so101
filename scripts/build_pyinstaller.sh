#!/usr/bin/env bash

set -euo pipefail

# 打包 SO101 节点为单文件可执行程序。
# 产物在本包 dist/robots_so101，中间文件在本包 build/pyinstaller/。
# 构建时会创建一次性隔离虚拟环境，依赖来自 uv.lock，避免受当前命令行环境影响。

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
DIST_DIR="${PACKAGE_DIR}/dist"
WORK_DIR="${PACKAGE_DIR}/build/pyinstaller"
VENV_DIR="${PACKAGE_DIR}/.venv_build"
REQUIREMENTS_FILE="${PACKAGE_DIR}/.venv_build.requirements.txt"

cd "${PACKAGE_DIR}"
mkdir -p "${DIST_DIR}" "${WORK_DIR}"
rm -rf "${VENV_DIR}"
rm -f "${REQUIREMENTS_FILE}"
rm -f "${DIST_DIR}/robots_so101" "${DIST_DIR}/robots_so101.exe"

cleanup() {
  rm -rf "${VENV_DIR}"
  rm -f "${REQUIREMENTS_FILE}"
}
trap cleanup EXIT

echo "==> [so101] 正在初始化隔离的局部构建虚拟环境..."
uv venv --no-workspace "${VENV_DIR}" --python 3.12

echo "==> [so101] 正在从 uv.lock 导出运行依赖..."
uv export \
  --project "${PACKAGE_DIR}" \
  --no-dev \
  --frozen \
  --no-hashes \
  --no-emit-project \
  --output-file "${REQUIREMENTS_FILE}"

echo "==> [so101] 正在同步依赖并安装 PyInstaller..."
uv pip sync --python "${VENV_DIR}/bin/python" "${REQUIREMENTS_FILE}"
uv pip install --python "${VENV_DIR}/bin/python" pyinstaller

echo "==> [so101] 开始使用 PyInstaller 进行打包..."
"${VENV_DIR}/bin/pyinstaller" \
  --noconfirm \
  --clean \
  --distpath "${DIST_DIR}" \
  --workpath "${WORK_DIR}" \
  "${SCRIPT_DIR}/robots_so101.spec"

EXE_NAME="robots_so101"
if [[ -f "${DIST_DIR}/${EXE_NAME}" ]]; then
  echo "OK: ${DIST_DIR}/${EXE_NAME}"
elif [[ -f "${DIST_DIR}/${EXE_NAME}.exe" ]]; then
  echo "OK: ${DIST_DIR}/${EXE_NAME}.exe"
else
  echo "WARNING: ${DIST_DIR}/${EXE_NAME} 未找到，请检查 PyInstaller 输出。" >&2
  exit 1
fi
