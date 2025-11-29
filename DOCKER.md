# Docker 部署指南

本文件說明如何使用 Docker 和 Docker Compose 部署 Financial Agent 服務。

## 前置需求

- Docker Engine 20.10 或更高版本
- Docker Compose 2.0 或更高版本

## 快速開始

### 1. 環境設定

複製環境變數範本並填入您的設定：

```bash
cp .env.example .env
```

編輯 `.env` 檔案，至少需要設定：
```env
OPENAI_API_KEY=your_actual_openai_api_key
```

### 2. 建置與啟動服務

使用 Docker Compose 建置並啟動所有服務：

```bash
# 建置映像檔
docker-compose build

# 啟動服務（背景執行）
docker-compose up -d

# 查看服務狀態
docker-compose ps

# 查看日誌
docker-compose logs -f
```

### 3. 存取服務

服務啟動後，可透過以下網址存取：

- **Streamlit UI**: http://localhost:8501
- **FastAPI API**: http://localhost:8000
- **API 文件**: http://localhost:8000/docs
- **健康檢查**: http://localhost:8000/health

## 服務架構

Docker Compose 部署包含兩個服務：

### API 服務 (`api`)
- **Port**: 8000
- **功能**: FastAPI RESTful API
- **健康檢查**: `/health` endpoint
- **容器名稱**: `financial-agent-api`

### UI 服務 (`ui`)
- **Port**: 8501
- **功能**: Streamlit Web 介面
- **健康檢查**: Streamlit 內建健康檢查
- **容器名稱**: `financial-agent-ui`
- **依賴**: 等待 API 服務健康後才啟動

## Docker 指令參考

### 基本操作

```bash
# 啟動服務
docker-compose up -d

# 停止服務
docker-compose down

# 重新啟動服務
docker-compose restart

# 停止並移除容器、網路、映像
docker-compose down --rmi all --volumes
```

### 查看狀態

```bash
# 查看運行中的容器
docker-compose ps

# 查看即時日誌
docker-compose logs -f

# 查看特定服務日誌
docker-compose logs -f api
docker-compose logs -f ui
```

### 重新建置

```bash
# 重新建置所有服務
docker-compose build

# 重新建置特定服務
docker-compose build api

# 不使用快取重新建置
docker-compose build --no-cache
```

### 執行指令

```bash
# 在 API 容器中執行指令
docker-compose exec api bash

# 在 UI 容器中執行指令
docker-compose exec ui bash

# 執行 Python 指令
docker-compose exec api python -c "print('Hello')"
```

## 開發模式

如需在開發時即時反映程式碼變更，可修改 `docker-compose.yaml`：

```yaml
services:
  api:
    volumes:
      - ./app:/app/app  # 掛載程式碼目錄
      - ./data:/app/data:ro
    environment:
      - API_RELOAD=true  # 啟用自動重載
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## 生產環境建議

### 1. 環境變數管理

生產環境不應使用 `.env` 檔案，建議使用：
- Docker Secrets
- Kubernetes Secrets
- AWS Parameter Store
- Azure Key Vault

### 2. 映像優化

```bash
# 建置生產映像
docker build -t financial-agent:latest .

# 推送至 Registry
docker tag financial-agent:latest your-registry/financial-agent:latest
docker push your-registry/financial-agent:latest
```

### 3. 資源限制

在 `docker-compose.yaml` 中加入資源限制：

```yaml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

### 4. 日誌管理

設定日誌驅動：

```yaml
services:
  api:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### 5. 健康檢查

兩個服務都已設定健康檢查，確保服務正常運行。

## 疑難排解

### 服務無法啟動

```bash
# 查看詳細錯誤訊息
docker-compose logs api
docker-compose logs ui

# 檢查容器狀態
docker-compose ps
```

### Port 被佔用

修改 `docker-compose.yaml` 中的 port mapping：

```yaml
ports:
  - "8080:8000"  # 使用 8080 代替 8000
```

### 資料持久化

如需保存日誌：

```yaml
volumes:
  - ./logs:/app/logs  # 掛載到本地目錄
```

### 網路問題

```bash
# 檢查 Docker 網路
docker network ls
docker network inspect financial-agent-network

# 重建網路
docker-compose down
docker-compose up -d
```

## 監控與維護

### 查看資源使用

```bash
# 查看容器資源使用情況
docker stats

# 查看特定容器
docker stats financial-agent-api financial-agent-ui
```

### 備份資料

```bash
# 備份資料目錄
tar -czf data-backup-$(date +%Y%m%d).tar.gz ./data

# 備份日誌
tar -czf logs-backup-$(date +%Y%m%d).tar.gz ./logs
```

## 安全性建議

1. **不要在映像中包含 `.env` 檔案**
2. **使用非 root 使用者執行容器**（已在 Dockerfile 中實作）
3. **定期更新基礎映像和依賴套件**
4. **限制容器權限**
5. **使用 HTTPS 在生產環境**
6. **設定防火牆規則**

## 更多資訊

- Docker 官方文件: https://docs.docker.com/
- Docker Compose 文件: https://docs.docker.com/compose/
- FastAPI 部署: https://fastapi.tiangolo.com/deployment/
- Streamlit 部署: https://docs.streamlit.io/deploy
