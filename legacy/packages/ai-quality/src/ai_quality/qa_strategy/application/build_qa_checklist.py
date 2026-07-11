"""Build final AI QA checklist."""

from __future__ import annotations

from typing import Any

from ai_quality.qa_strategy.domain.qa_checklist import QAChecklist, QAChecklistItem


# docs:start build_qa_checklist
def build_qa_checklist(config: dict[str, Any]) -> QAChecklist:
    """Build checklist items from config."""
    items: list[QAChecklistItem] = []
    for section, texts in config["sections"].items():
        for text in texts:
            items.append(
                QAChecklistItem(
                    section=str(section),
                    text=str(text),
                )
            )

    return QAChecklist(items=tuple(items))
# docs:end build_qa_checklist
