# 中医适宜技术助手（移动端）

本项目为院赛演示版，分为两部分：

- `app-mobile`：Expo 手机端（首页、知识库、智能问答、管理）
- `backend`：本地 Python 后端（知识库检索、问答代理、会话记忆）

当前版本已完成以下优化：

- 全中文界面
- 知识库详情页展示完整正文
- 去除教材配图模块（只保留文本知识）
- 启动脚本自动读取 `backend/local_config.json` 中的 API Key

## 一键启动

先启动后端（会自动读取本地配置里的 API Key）：

```powershell
powershell -ExecutionPolicy Bypass -File "D:\Desktop\中医适宜技术知识库\UI\backend\run_backend.ps1"
```

再启动手机预览：

```powershell
powershell -ExecutionPolicy Bypass -File "D:\Desktop\中医适宜技术知识库\UI\run_mobile_preview.ps1" -Clear
```

也可以一条命令同时启动：

```powershell
powershell -ExecutionPolicy Bypass -File "D:\Desktop\中医适宜技术知识库\UI\run_demo.ps1" -Clear
```

## 依赖安装（首次）

```powershell
cd "D:\Desktop\中医适宜技术知识库\UI\app-mobile"
npm install
```

## 说明

- 手机和电脑需在同一局域网。
- `run_mobile_preview.ps1` 会自动写入手机端后端地址到 `app-mobile/src/generated/runtimeConfig.ts`。
- 若端口被占用，脚本会自动选择 8090-8120 的空闲端口。
