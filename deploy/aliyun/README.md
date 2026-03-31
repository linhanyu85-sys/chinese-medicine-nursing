# 阿里云 ECS 部署说明

这套部署脚本默认把后端单独放到独立目录和独立端口，不会覆盖你服务器上已有项目。

## 默认参数

- 代码目录：`/opt/tcm-knowledge-nursing`
- 服务名：`tcm-knowledge-backend`
- 环境变量：`/etc/tcm-knowledge-backend.env`
- 端口：`18791`

## 先准备两样东西

1. 模型 Key
2. 教材 docx 文件

注意：

- 教材文件不要放进 Git 仓库
- 把教材单独上传到服务器本地目录，例如 `/opt/tcm-knowledge-data/`
- 在环境变量文件中配置 `KB_DOCX_PATH`

## 第一次部署

```bash
git clone https://github.com/linhanyu85-sys/chinese-medicine-nursing.git /opt/tcm-knowledge-nursing
sudo bash /opt/tcm-knowledge-nursing/deploy/aliyun/deploy_backend.sh
```

如果已经拉过代码：

```bash
sudo bash /opt/tcm-knowledge-nursing/deploy/aliyun/deploy_backend.sh
```

## 修改环境变量

编辑：

```bash
sudo nano /etc/tcm-knowledge-backend.env
```

至少补齐：

```bash
ALIYUN_API_KEY=你的阿里百炼Key
KB_DOCX_PATH=/opt/tcm-knowledge-data/中医护理适宜技术合稿.docx
```

如果教材路径改了，重启服务即可重新加载：

```bash
sudo systemctl restart tcm-knowledge-backend
```

## 检查服务

本机检查：

```bash
curl http://127.0.0.1:18791/api/health
```

外网检查：

```bash
curl http://<ECS公网IP>:18791/api/health
```

如果外网访问失败，通常检查两项：

- 阿里云安全组是否放行 `18791/TCP`
- 服务器防火墙是否放行 `18791`

## 说明

- 会话数据保存在服务器本地 `backend/data/session_memory.json`
- 知识缓存保存在服务器本地 `backend/data/knowledge_cache.json`
- 这两个文件都不需要回传 Git
