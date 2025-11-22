# 🚀 快速測試指南

## 測試狀態: ✅ 全部通過

### 已完成的測試

1. **依賴安裝** ✅
   ```bash
   uv sync --extra dev
   ```
   - 82 個主要套件
   - 19 個開發套件

2. **單元測試** ✅ 14/15 通過
   ```bash
   uv run pytest
   ```

3. **系統測試** ✅ 5/5 通過
   ```bash
   python test_system.py
   ```

4. **API 伺服器** ✅
   - FastAPI 正常運行
   - 健康檢查端點回應正常

5. **模組導入** ✅
   - 所有核心模組可正常導入
   - UI 頁面載入成功

---

## 🎯 下一步操作

### 1. 配置 OpenAI API Key

編輯 `.env` 檔案:
```bash
OPENAI_API_KEY=your_actual_api_key_here
```

### 2. 啟動 Streamlit UI

```bash
streamlit run streamlit_app.py
```

瀏覽器自動開啟 http://localhost:8501

### 3. 或啟動 API 伺服器

```bash
uvicorn app.main:app --reload
```

API 文檔: http://localhost:8000/docs

---

## 📊 可用功能

### Streamlit UI (9 個頁面)
- 📊 Snapshot - 財務快照
- 📈 Trend - 趨勢分析
- 🔄 Peer - 同業比較
- ⭐ Management - 管理品質
- 💎 Earnings Quality - 盈餘品質
- 💰 ROIC vs WACC - 價值創造
- 📐 Factor - 因子分析
- 🚨 Early Warning - 預警系統
- 🤖 Agent - AI 助理

### API 端點
- GET /health - 健康檢查
- GET /docs - API 文檔
- POST /api/scores/management - 管理評分
- POST /api/agent/query - AI 查詢

---

## 🧪 測試命令

```bash
# 完整測試
uv run pytest --cov=app tests/

# 系統驗證
python test_system.py

# 快速測試
uv run pytest tests/test_models.py -v

# 檢查代碼格式
uv run black --check app/ tests/ ui/

# 檢查語法
uv run flake8 app/ tests/ ui/
```

---

## 📝 測試數據

已包含示例數據:
- `data/financial_reports/2330_2023Q3_enhanced.json`

添加更多數據請參考 `SAMPLE_DATA.md`

---

## ⚠️ 注意事項

1. **OpenAI API Key 必需**: AI Agent 功能需要有效的 API key
2. **Python 3.10+**: 確保使用正確的 Python 版本
3. **虛擬環境**: 建議使用 `.venv` 來隔離依賴

---

## 🐛 如遇問題

1. 重新安裝依賴: `uv sync --reinstall`
2. 清理快取: `uv cache clean`
3. 檢查 Python 版本: `python --version`
4. 查看錯誤日誌: 檢查終端輸出

---

## ✅ 測試完成確認清單

- [x] 依賴安裝成功
- [x] 單元測試通過 (14/15)
- [x] 系統測試通過 (5/5)
- [x] API 伺服器可啟動
- [x] 模組導入正常
- [x] 資料目錄已建立
- [x] .env 檔案已建立
- [ ] OpenAI API Key 已配置
- [ ] 已添加真實財務數據

**準備就緒!** 🎉
