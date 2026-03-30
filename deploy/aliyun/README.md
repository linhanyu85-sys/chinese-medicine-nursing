# 阿里云 ECS 部署（隔离模式）

本目录用于把项目后端部署到阿里云 ECS，默认采用独立目录、独立服务、独立端口，不会覆盖你服务器已有项目。

## 默认隔离参数

- 代码目录：`/opt/tcm-knowledge-nursing`
- 服务名：`tcm-knowledge-backend`
- 环境变量：`/etc/tcm-knowledge-backend.env`
- 对外端口：`18791`

## 服务器上执行

```bash
sudo bash /opt/tcm-knowledge-nursing/stitch/deploy/aliyun/deploy_backend.sh
```

如果第一次执行时还没拉代码，可先：

```bash
git clone https://github.com/linhanyu85-sys/chinese-medicine-nursing.git /opt/tcm-knowledge-nursing
sudo bash /opt/tcm-knowledge-nursing/stitch/deploy/aliyun/deploy_backend.sh
```

## 修改 API Key

编辑：

```bash
sudo nano /etc/tcm-knowledge-backend.env
```

设置：

```bash
ALIYUN_API_KEY=你的阿里百炼Key
```

然后重启：

```bash
sudo systemctl restart tcm-knowledge-backend
```

## 检查

```bash
curl http://127.0.0.1:18791/api/health
```

外网访问：

`http://<ECS公网IP>:18791/api/health`

如无法访问，请放行阿里云安全组端口 `18791/TCP`。
