# 中医适宜技术助手

这是一个面向临床护理场景的移动端知识助手，分成两部分：

- `app-mobile`：Expo 移动端，提供首页、知识库、智能问答、管理
- `backend`：Python 后端，负责教材解析、混合检索、病例问答、会话历史

这次版本重点不是“把教材做成搜索框”，而是把它改成更接近临床实际使用的工具：

- 支持病例式输入，不再只靠单个关键词命中
- 智能问答输出统一为纯文本六段式，避免 `#`、`*`、表格残片
- 支持新建对话隔离上下文，并可查看历史会话
- 教材正文不再随仓库上传，知识缓存仅本地生成

## 目录

```text
UI/
├─ app-mobile/          Expo App
├─ backend/             检索、问答、会话后端
├─ deploy/aliyun/       阿里云 ECS 部署脚本
└─ xuan_clinical_essence/
```

## 当前问答链路

1. 手机端提交护理问题或完整病例
2. 后端抽取病例字段
   - 主诉
   - 现病史
   - 生命体征
   - 疼痛评分
   - 危险征象
   - 舌脉线索
3. 检索层做混合召回
   - 关键词
   - BM25
   - 轻量语义向量
   - 病例主诉和证候线索加权
4. 生成层输出固定结构
   - 病情摘要
   - 护理判断
   - 护理建议
   - 观察与上报
   - 护理记录
   - 依据条目
5. 会话层保存每轮问答，支持历史查看和新会话隔离

## 快速启动

先启动后端：

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

## 首次安装

前端：

```powershell
cd "D:\Desktop\中医适宜技术知识库\UI\app-mobile"
npm install
```

后端：

```powershell
cd "D:\Desktop\中医适宜技术知识库\UI\backend"
python -m pip install -r requirements.txt
```

`run_backend.ps1` 会在缺少 `python-docx` 时自动补装。

## 教材文件说明

仓库不再携带教材正文，也不要把教材文件提交到 Git。

后端支持两种本地加载方式：

1. 在 `backend/local_config.json` 中配置 `docxPath`
2. 设置环境变量 `KB_DOCX_PATH`

示例：

```json
{
  "apiKey": "你的模型Key",
  "baseUrl": "https://coding.dashscope.aliyuncs.com/v1",
  "model": "kimi-k2.5",
  "docxPath": "D:\\Desktop\\(终版2.11）中医护理适宜技术合稿 方正后.docx"
}
```

首次加载成功后，后端会在本地生成 `backend/data/knowledge_cache.json` 作为缓存。这个文件已加入 `.gitignore`，不会再上传仓库。

## 智能问答页变化

- 支持病例识别
- 支持新建对话
- 支持历史会话切换
- 支持本会话记录回看
- 输出格式统一，便于手机端阅读和护理记录

## Android APK

本项目使用 EAS 构建 APK：

```powershell
cd "D:\Desktop\中医适宜技术知识库\UI"
powershell -ExecutionPolicy Bypass -File ".\build_android_apk.ps1"
```

如果要把 APK 固定连接到线上后端，可先设置：

```powershell
$env:APP_BACKEND_URL = "http://你的ECS公网IP:18791"
```

## 阿里云部署

部署脚本位于：

```text
deploy/aliyun/
```

部署时请注意两点：

- 模型 Key 放在服务器环境变量文件中
- 教材 docx 放在服务器本地目录，不要跟代码仓库一起上传

部署说明见：

- `deploy/aliyun/README.md`
- `deploy/aliyun/tcm_knowledge_backend.env.example`

## 开发说明

- 会话数据保存在 `backend/data/session_memory.json`
- 知识缓存保存在 `backend/data/knowledge_cache.json`
- 前端后端地址写入 `app-mobile/src/generated/runtimeConfig.ts`

## 注意

- 手机和电脑需要在同一局域网，除非使用已部署的公网后端
- 如果端口被占用，预览脚本会自动选择可用端口
- 若更换了教材文件，进入管理页后点击“刷新知识库”即可重新解析
