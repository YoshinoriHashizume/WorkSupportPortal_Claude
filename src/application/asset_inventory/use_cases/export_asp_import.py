from __future__ import annotations

import enum
from dataclasses import dataclass

from application.asset_inventory.domain.value_objects.asp_import import (
    EMPTY_MESSAGE,
    UNAVAILABLE_MESSAGE,
    AmendmentRows,
)
from application.asset_inventory.domain.value_objects.reconcile_cache import (
    load_amendment_snapshot,
)
from application.asset_inventory.use_cases.list_page import ListPageQuery


class AspImportStatus(enum.Enum):
    """取り込み用データ作成の結果区分（design.md §8.2）。"""

    OK = "ok"
    EMPTY = "empty"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class AspImportResult:
    """ASP 取り込み用データ（V-306）の作成結果。

    `status` が `OK` のときだけ `content` に CSV が入る。業務的な分岐は例外ではなく
    この区分で表現する（design.md §8.2）。
    """

    status: AspImportStatus
    content: bytes | None = None
    row_count: int = 0
    message: str = ""
    warning_message: str = ""


class ExportAspImport:
    """修正対象行（V-307）から ASP 取り込み用データを作成する（REQ-ASP-IMPORT-DATA-2026-001）。

    画面が表示した突合結果スナップショットだけを入力とし、desknet's へは一切問い合わせない
    （REQ-NF-003・DD-01）。そのためゲートウェイを受け取らない。
    """

    def execute(self, query: ListPageQuery, session: dict | None = None) -> AspImportResult:
        """選択中の棚卸の修正対象行から CSV を組み立てる。"""
        cache = load_amendment_snapshot(session, query.management_id)
        if cache is None:
            # 棚卸未選択・スナップショット無し・棚卸不一致・セッション破損のいずれか（REQ-F-009）
            return AspImportResult(
                status=AspImportStatus.UNAVAILABLE, message=UNAVAILABLE_MESSAGE
            )

        # 画面のフィルタ・ソートには依存せず、選択中の棚卸の全行を対象とする（REQ-F-002）
        amendments = AmendmentRows.select_from(cache.rows)
        if amendments.is_empty():
            return AspImportResult(status=AspImportStatus.EMPTY, message=EMPTY_MESSAGE)

        import_rows = amendments.to_import_rows(site_warning=cache.site_warning)
        return AspImportResult(
            status=AspImportStatus.OK,
            content=import_rows.render_csv(),
            row_count=amendments.count(),
            warning_message=import_rows.warnings().message(),
        )
