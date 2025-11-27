"""
財報資料格式轉換腳本
將爬蟲產生的巢狀 JSON 格式轉換成專案所需的扁平化格式
"""

import json
import sys
from pathlib import Path


def convert_report(input_file: str, output_file: str = None) -> None:
    """
    轉換財報 JSON 格式
    
    Args:
        input_file: 輸入的 JSON 檔案路徑 (爬蟲產生的格式)
        output_file: 輸出的 JSON 檔案路徑 (可選,預設自動生成)
    """
    # 讀取原始資料
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 提取季度數字 (從 "Q2" 轉換為 2)
    report_season = data.get('report_season', 'Q1')
    if isinstance(report_season, str) and report_season.startswith('Q'):
        season_num = int(report_season[1:])
    else:
        season_num = int(report_season)
    
    # 建立扁平化的資料結構
    converted = {
        "stock_code": data.get('stock_code', ''),
        "company_name": data.get('company_name', ''),
        "report_year": data.get('report_year', 0),
        "report_season": season_num,
        "report_period": data.get('report_period', ''),
        "currency": data.get('currency', 'TWD'),
        "unit": "thousand",  # 統一為 thousand
    }
    
    # 從 financials 或 financial_data 中提取資產負債表數據
    financials = data.get('financials', data.get('financial_data', {}))
    
    converted.update({
        "cash_and_equivalents": financials.get('cash_and_equivalents', 0),
        "accounts_receivable": financials.get('accounts_receivable', 0),
        "inventory": financials.get('inventory', 0),
        "total_assets": financials.get('total_assets', 0),
        "total_liabilities": financials.get('total_liabilities', 0),
        "equity": financials.get('equity', 0),
    })
    
    # 從 income_statement 或 financial_data 中提取損益表數據
    income = data.get('income_statement', financials)
    
    converted.update({
        "net_revenue": income.get('net_revenue', 0),
        "gross_profit": income.get('gross_profit', 0),
        "operating_income": income.get('operating_income', 0),
        "net_income": income.get('net_income', 0),
        "eps": income.get('eps', 0.0),
    })
    
    # 決定輸出檔名
    if output_file is None:
        stock_code = converted['stock_code']
        report_period = converted['report_period']
        output_file = f"data/financial_reports/{stock_code}_{report_period}_enhanced.json"
    
    # 建立輸出目錄
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 寫入轉換後的資料
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(converted, f, ensure_ascii=False, indent=2)
    
    print(f"✓ 轉換完成: {input_file} -> {output_file}")
    print(f"  股票代碼: {converted['stock_code']} ({converted['company_name']})")
    print(f"  報告期間: {converted['report_period']}")
    print(f"  EPS: {converted['eps']}")


def batch_convert(input_dir: str, output_dir: str = None) -> None:
    """
    批次轉換目錄中的所有 JSON 檔案
    
    Args:
        input_dir: 輸入目錄路徑
        output_dir: 輸出目錄路徑 (可選)
    """
    input_path = Path(input_dir)
    
    if not input_path.exists():
        print(f"❌ 錯誤: 目錄不存在 {input_dir}")
        return
    
    json_files = list(input_path.glob("*.json"))
    
    if not json_files:
        print(f"⚠ 警告: 在 {input_dir} 中找不到 JSON 檔案")
        return
    
    print(f"找到 {len(json_files)} 個 JSON 檔案")
    print("-" * 60)
    
    for json_file in json_files:
        try:
            if output_dir:
                output_file = Path(output_dir) / f"{json_file.stem}_converted.json"
            else:
                output_file = None
            
            convert_report(str(json_file), str(output_file) if output_file else None)
        except Exception as e:
            print(f"❌ 轉換失敗 {json_file.name}: {e}")
    
    print("-" * 60)
    print(f"✓ 批次轉換完成")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方式:")
        print("  單一檔案: python convert_financial_report.py <input_file> [output_file]")
        print("  批次處理: python convert_financial_report.py --batch <input_dir> [output_dir]")
        print()
        print("範例:")
        print("  python convert_financial_report.py 202402_3661_AI1_enhanced.json")
        print("  python convert_financial_report.py 202402_3661_AI1_enhanced.json 3661_2024Q2_enhanced.json")
        print("  python convert_financial_report.py --batch ./raw_data ./processed_data")
        sys.exit(1)
    
    if sys.argv[1] == "--batch":
        input_dir = sys.argv[2] if len(sys.argv) > 2 else "."
        output_dir = sys.argv[3] if len(sys.argv) > 3 else None
        batch_convert(input_dir, output_dir)
    else:
        input_file = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else None
        convert_report(input_file, output_file)
