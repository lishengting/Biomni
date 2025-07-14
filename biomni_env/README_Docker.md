# Biomni Docker 部署指南

## 概述

由于Conda开始收费，我们提供了基于Docker的替代部署方案。Docker部署具有以下优势：

- ✅ **免费**：完全免费，无需付费许可证
- ✅ **隔离**：环境完全隔离，不会影响系统
- ✅ **可移植**：在任何支持Docker的系统上运行
- ✅ **一致性**：确保在不同机器上运行结果一致
- ✅ **易管理**：一键部署和管理

## 环境选择

### 1. 基础环境（Basic）
- **用途**：快速体验AI代理功能
- **包含**：Python基础包 + AI/ML工具
- **构建时间**：~5-10分钟
- **镜像大小**：~2GB

### 2. 完整环境（Full）
- **用途**：完整的生物信息学研究
- **包含**：所有生物信息学工具 + R环境 + 命令行工具
- **构建时间**：~30-60分钟
- **镜像大小**：~8-10GB

### 3. 开发环境（Dev）
- **用途**：开发和调试
- **包含**：基础环境 + 源代码挂载
- **构建时间**：~5-10分钟
- **镜像大小**：~2GB

## 快速开始

### 前置要求

1. **安装Docker**
   ```bash
   # Ubuntu/Debian
   sudo apt-get update
   sudo apt-get install docker.io docker-compose
   sudo systemctl start docker
   sudo systemctl enable docker
   
   # 或者使用官方安装脚本
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh
   ```

2. **添加用户到docker组**（可选，避免使用sudo）
   ```bash
   sudo usermod -aG docker $USER
   # 重新登录生效
   ```

### 部署步骤

1. **克隆项目**
   ```bash
   git clone https://github.com/snap-stanford/Biomni.git
   cd Biomni/biomni_env
   ```

2. **给部署脚本执行权限**
   ```bash
   chmod +x deploy.sh
   ```

3. **选择环境并部署**

   **基础环境（推荐新手）**：
   ```bash
   ./deploy.sh basic
   ```

   **完整环境（推荐研究人员）**：
   ```bash
   ./deploy.sh full
   ```

   **开发环境（推荐开发者）**：
   ```bash
   ./deploy.sh dev
   ```

## 使用说明

### 访问服务

部署完成后，可以通过以下地址访问：

- **基础环境**：
  - Jupyter Notebook: http://localhost:8888 或 http://你的IP:8888
  - Gradio: http://localhost:7860 或 http://你的IP:7860

- **完整环境**：
  - Jupyter Notebook: http://localhost:8889 或 http://你的IP:8889
  - Gradio: http://localhost:7861 或 http://你的IP:7861

- **开发环境**：
  - Jupyter Notebook: http://localhost:8890 或 http://你的IP:8890
  - Gradio: http://localhost:7862 或 http://你的IP:7862

**注意**：现在服务已配置为允许外部访问，你可以从任何网络设备访问这些服务。

### 管理容器

```bash
# 查看帮助
./deploy.sh help

# 停止所有容器
./deploy.sh stop

# 查看日志
./deploy.sh logs basic    # 查看基础环境日志
./deploy.sh logs full     # 查看完整环境日志

# 进入容器shell
./deploy.sh shell basic   # 进入基础环境shell
./deploy.sh shell full    # 进入完整环境shell

# 清理所有容器和镜像
./deploy.sh clean
```

### 数据持久化

项目目录结构：
```
biomni_env/
├── data/          # 数据目录（挂载到容器）
├── notebooks/     # Jupyter notebooks（挂载到容器）
├── results/       # 结果目录（仅完整环境）
└── src/           # 源代码（仅开发环境）
```

所有数据都会保存在宿主机的对应目录中，容器重启不会丢失。

## 手动Docker命令

如果不使用部署脚本，也可以手动使用Docker命令：

### 构建镜像
```bash
# 构建基础环境
docker build -f Dockerfile.basic -t biomni-basic .

# 构建完整环境
docker build -f Dockerfile -t biomni-full .
```

### 运行容器
```bash
# 运行基础环境
docker run -d -p 8888:8888 -p 7860:7860 \
  -v $(pwd)/data:/opt/biomni/data \
  -v $(pwd)/notebooks:/opt/biomni/notebooks \
  --name biomni-basic biomni-basic

# 运行完整环境
docker run -d -p 8889:8888 -p 7861:7860 \
  -v $(pwd)/data:/opt/biomni/data \
  -v $(pwd)/notebooks:/opt/biomni/notebooks \
  -v $(pwd)/results:/opt/biomni/results \
  --name biomni-full biomni-full
```

### 进入容器
```bash
# 进入基础环境
docker exec -it biomni-basic /bin/bash

# 进入完整环境
docker exec -it biomni-full /bin/bash
```

## 环境对比

| 特性 | Conda方案 | Docker方案 |
|------|-----------|------------|
| 费用 | 收费 | 免费 |
| 安装时间 | 10+小时（完整） | 30-60分钟（完整） |
| 环境隔离 | 部分 | 完全 |
| 可移植性 | 中等 | 高 |
| 管理复杂度 | 高 | 低 |
| 磁盘空间 | 30GB+ | 8-10GB |

## 故障排除

### 常见问题

1. **端口被占用**
   ```bash
   # 查看端口占用
   sudo netstat -tulpn | grep :8888
   
   # 停止占用端口的进程
   sudo kill -9 <PID>
   ```

2. **权限问题**
   ```bash
   # 确保用户有Docker权限
   sudo usermod -aG docker $USER
   # 重新登录
   ```

3. **磁盘空间不足**
   ```bash
   # 清理Docker缓存
   docker system prune -a
   ```

4. **网络问题**
   ```bash
   # 检查Docker网络
   docker network ls
   docker network inspect biomni_env_default
   ```

5. **外部访问问题**
   ```bash
   # 检查防火墙设置
   sudo ufw status
   
   # 如果需要，开放端口
   sudo ufw allow 8888
   sudo ufw allow 7860
   
   # 检查服务状态
   docker ps
   docker logs biomni-basic  # 或 biomni-full, biomni-dev
   ```

6. **服务启动失败**
   ```bash
   # 查看详细日志
   docker logs -f biomni-basic
   
   # 重新构建镜像
   ./deploy.sh clean
   ./deploy.sh build basic
   ./deploy.sh basic
   ```

### 日志查看

```bash
# 查看容器状态
docker ps -a

# 查看详细日志
docker logs biomni-basic
docker logs biomni-full

# 实时查看日志
docker logs -f biomni-basic
```

## 性能优化

### 资源限制

可以在`docker-compose.yml`中添加资源限制：

```yaml
services:
  biomni-full:
    # ... 其他配置
    deploy:
      resources:
        limits:
          memory: 8G
          cpus: '4'
        reservations:
          memory: 4G
          cpus: '2'
```

### 构建优化

1. **使用多阶段构建**减少镜像大小
2. **并行安装**包以提高构建速度
3. **清理缓存**减少镜像大小

## 更新和维护

### 更新镜像
```bash
# 重新构建镜像
./deploy.sh build basic
./deploy.sh build full

# 重启服务
./deploy.sh stop
./deploy.sh basic  # 或 full
```

### 备份数据
```bash
# 备份数据目录
tar -czf biomni_data_backup.tar.gz data/ notebooks/ results/

# 恢复数据
tar -xzf biomni_data_backup.tar.gz
```

## 贡献

欢迎提交Issue和Pull Request来改进Docker部署方案！

## 许可证

本项目遵循原项目的许可证。 