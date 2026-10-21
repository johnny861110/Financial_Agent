"""Tests for the composer rules enforced after the answer is written.

The prompt forbids attaching a passage citation to a figure and writing an
empty section such as "矛盾：無". The model broke both while being told not
to, so they are checked in code once the answer exists.
"""

import inspect

from app.agents.workflow import FinancialAgent, _enforce_answer_rules

RETRIEVED = [
    {"chunk_id": 472997, "section_title": "附表一", "page_number": 54},
    {"chunk_id": 100, "section_title": "會計政策", "page_number": 20},
    {"chunk_id": 101, "section_title": "市場風險", "page_number": 39},
]


def test_citation_closing_a_paragraph_of_figures_is_removed():
    """The 2026Q2 answer that prompted this check."""
    answer = (
        "台積電在2026Q2的淨利為7,067.81億元，營業利益率為60.34%。投資論點為中性。"
        "【附表一 · p.54 · chunk 472997】"
    )

    cleaned, removed = _enforce_answer_rules(answer, RETRIEVED)

    assert "chunk 472997" not in cleaned
    assert "7,067.81億元" in cleaned
    assert removed == ["passage citation attached to a figure: 附表一 · p.54 · chunk 472997"]


def test_citation_inside_a_sentence_with_a_figure_is_removed():
    answer = "毛利率為 62.33% [財務報表 · p.10 · chunk 100]，表現穩定。"

    cleaned, _ = _enforce_answer_rules(answer, RETRIEVED)

    assert cleaned == "毛利率為 62.33% ，表現穩定。"


def test_citation_for_a_narrative_claim_is_kept():
    answer = (
        "淨利為 230.74 億元。公司採用預期信用損失模型評估應收帳款 [會計政策 · p.20 · chunk 100]。"
        "\n\n結論：中性。"
    )

    cleaned, removed = _enforce_answer_rules(answer, RETRIEVED)

    assert "[會計政策 · p.20 · chunk 100]" in cleaned
    assert removed == []


def test_citation_after_a_mid_paragraph_full_stop_judges_only_its_sentence():
    answer = "營收為 1,501.88 億元。公司說明需求來自 AI 客戶。[營運概況 · p.5 · chunk 100] 下一段。"

    cleaned, removed = _enforce_answer_rules(answer, RETRIEVED)

    assert "chunk 100" in cleaned
    assert removed == []


def test_citation_to_a_passage_that_was_not_retrieved_is_removed():
    answer = "公司說明產能利用率提升 [營運概況 · p.5 · chunk 999]。"

    cleaned, removed = _enforce_answer_rules(answer, RETRIEVED)

    assert "chunk 999" not in cleaned
    assert removed == ["citation to a passage that was not retrieved: 營運概況 · p.5 · chunk 999"]


def test_empty_sections_are_removed():
    answer = (
        "結論：中性\n\n矛盾：無\n\n- 風險：無。\n\n**矛盾訊號**：無\n\n資料缺口：\n- eps_diluted"
    )

    cleaned, removed = _enforce_answer_rules(answer, RETRIEVED)

    assert cleaned == "結論：中性\n\n資料缺口：\n- eps_diluted"
    assert len(removed) == 3


def test_a_section_with_content_that_starts_with_none_is_kept():
    answer = "風險：無明顯財務壓力，但應計項目偏高。"

    cleaned, removed = _enforce_answer_rules(answer, RETRIEVED)

    assert cleaned == answer
    assert removed == []


def test_citation_without_a_chunk_id_is_checked_by_section_and_page():
    """The model also writes 【市場風險 · p.39】, dropping the chunk id."""
    answer = "公司面臨匯率風險。【市場風險 · p.39】\n\n毛利率 67.72%。【市場風險 · p.39】"

    cleaned, removed = _enforce_answer_rules(answer, RETRIEVED)

    assert cleaned == "公司面臨匯率風險。【市場風險 · p.39】\n\n毛利率 67.72%。"
    assert removed == ["passage citation attached to a figure: 市場風險 · p.39"]


def test_citation_without_a_chunk_id_to_an_unretrieved_page_is_removed():
    answer = "公司面臨匯率風險。【市場風險 · p.40】"

    cleaned, removed = _enforce_answer_rules(answer, RETRIEVED)

    assert cleaned == "公司面臨匯率風險。"
    assert removed == ["citation to a passage that was not retrieved: 市場風險 · p.40"]


def test_composer_applies_the_rules_to_the_model_answer():
    source = inspect.getsource(FinancialAgent._answer_composer_node)

    assert "_enforce_answer_rules(" in source
