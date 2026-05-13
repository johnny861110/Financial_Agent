# 📑 Financial Intelligence Agent (FIA) 系統升級技術規格書 (Technical Specification)

**版本**: v2.0-Quant-Focus  
**狀態**: 需求開發中  
**目標**: 將 FIA 從靜態原型轉化為具備「業界標準估計法」與「多智能體對抗架構」的專業投研平台。

> Implementation note: this document is the target roadmap. The current runtime
> is a JSON-file-based FastAPI/Streamlit/LangGraph application. PostgreSQL,
> Redis, pgvector, market-data beta estimation, multi-agent debate, PDF export,
> and full RAG ingestion are not yet implemented.

---

## 1. 系統願景 (Project Vision)
構建一個能夠自動化執行深度財務審查、精準因子計算並產出具備邏輯說服力之投資建議書（Investment Memo）的 AI 專家系統。

---

## 2. 核心量化因子規格 (Industry-Standard Quant Specs)
從「固定數值」改為基於真實財報數據的「動態估計模型」。

### 2.1 價值創造模型 (Value Creation - ROIC/WACC)
*   **ROIC (資本回報率)**:
    *   **公式**: $ROIC = NOPAT / Invested\ Capital$
    *   **NOPAT**: $EBIT 	imes (1 - Effective\ Tax\ Rate)$
    *   **Invested Capital**: $(總負債 + 總權益 - 現金及約當財物 - 無息流動負債)$
*   **WACC (加權平均資本成本)**:
    *   **Equity Cost ($Re$)**: 採用 CAPM 模型 ($Re = Rf + \beta 	imes (Rm - Rf)$)
    *   **Debt Cost ($Rd$)**: $利息支出 / 平均總負債 	imes (1 - T)$
    *   **Beta ($\beta$)**: 個股對應大盤之 24 個月滾動協方差係數。

### 2.2 獲利品質模組 (Earnings Quality)
*   **Sloan's Accrual Analysis**:
    *   **指標**: $(Net\ Income - CFO) / Average\ Total\ Assets$
    *   **標準**: 指標 > 0.1 視為紅旗訊號，代表盈餘主要由非現金項組成。
*   **營運資本分析**: 追蹤應收帳款周轉天數 (DSO) 與存貨周轉天數 (DII) 的異常偏離。

### 2.3 破產預警模型 (Altman Z-Score)
*   **權重指標**: 結合營運資金比率、留存收益比率、EBIT/總資產、市值/總負債及營業收入/總資產。

---

## 3. 多智能體協作架構 (A2A Architecture)
將工作流升級為「紅藍對抗」模式，確保分析結論不受單一 LLM 偏誤影響。

### 3.1 角色定義
*   **Bull Analyst (多頭分析師)**: 負責尋找增長動力、毛利提升空間與市場護城河。
*   **Bear Auditor (空頭審計師)**: 負責挖掘財報漏洞、現金流異常與資本配置效率低落點。
*   **Portfolio Manager (PM 決策者)**: 負責聽取雙方辯論，根據因子分數與風控要求，給出最終投資評級。

### 3.2 狀態管理 (Memory & State)
*   **短期記憶**: 使用 LangGraph `messages` 儲存 Agent 間的辯論過程。
*   **長期記憶**: 透過 **PostgreSQL Checkpointer** 儲存每個 `thread_id` 的決策樹快照。

---

## 4. 數據層架構 (Data Ingestion & Storage)

### 4.1 數據補足清單 (Data Gaps)
為了支撐上述公式，系統必須對接以下數據：
1.  **現金流量表**: 營業現金流 (CFO)、資本支出 (CapEx)。
2.  **損益表細節**: EBIT、利息支出、所得稅費用。
3.  **市場數據**: 每日收盤價 (用於 Beta 與 Momentum)、發行股數 (用於市值計算)。
4.  **宏觀數據**: 無風險利率 (10Y Treasury Rate)。

### 4.2 技術組件
*   **PostgreSQL**: 儲存結構化財報數據、因子快照與 Agent Checkpoints。
*   **Redis**: 快取外部 API（如 yfinance, FMP）的回應。
*   **Vector DB (pgvector)**: 儲存財報 PDF 的嵌入向量，支援語義檢索。

---

## 5. 自動化投資報告 (Investment Memo) 規格

### 5.1 報告結構
1.  **Executive Summary**: 核心評級 (Buy/Hold/Sell) 與目標價範圍。
2.  **Quant Scorecard**: ROIC, Sloan Accrual, Z-Score 的量化評分與排名。
3.  **Fundamental Analysis**: 成長趨勢、獲利品質與競爭優勢。
4.  **Risk Disclosure**: 財務紅旗、地緣政治與管理層指引偏差。
5.  **A2A Debate Summary**: 記錄分析師與審計師的關鍵衝突點及 PM 的裁決邏輯。

### 5.2 導出格式
*   **Markdown**: 用於內部系統顯示。
*   **PDF**: 透過 `xhtml2pdf` 生成正式文檔。

---

## 6. 系統開發時程 (Roadmap)
1.  **Sprint 1**: 基礎設施建設（Postgres + Redis Docker 化、yfinance API 對接）。
2.  **Sprint 2**: 量化引擎升級（實作 NOPAT, WACC, Sloan Accrual 數學計算邏輯）。
3.  **Sprint 3**: A2A 工作流開發（建立對抗性 Prompt 節點與 PM 裁決邏輯）。
4.  **Sprint 4**: 報告生成模組（Markdown 轉 PDF 引擎、視覺化圖表自動整合）。

---

## 7. 結論
透過此規格書的實施，專案將進化為一個具有深度財務洞察力、可解釋決策過程以及標準化產出的專業量化研究系統。
