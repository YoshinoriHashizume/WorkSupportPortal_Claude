from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from apps.asset_inventory.domain.row_detail import FieldDiffItem
    from apps.asset_inventory.domain.table_display import SortSpec


class MatchStatus(str, Enum):
    MATCHED = "matched"
    ASSET_ONLY = "asset_only"
    INVENTORY_ONLY = "inventory_only"


class RowTone(str, Enum):
    NONE = "NONE"
    MATCH_CLEAN = "MATCH_CLEAN"
    MATCH_DIFF = "MATCH_DIFF"
    MATCH_FACTORY = "MATCH_FACTORY"


Record = dict[str, str]


@dataclass(frozen=True)
class ManagementRow:
    data_id: str
    inventory_name: str
    fiscal_year: str
    company_app_id: str
    site_app_id: str
    asset_app_id: str
    inventory_app_id: str


@dataclass(frozen=True)
class ReconcileRow:
    match_status: MatchStatus
    row_tone: RowTone
    status_label: str
    tone_label: str
    asset_number: str
    branch_number: str
    site_name: str
    manufacturer: str
    model_name: str
    serial_number: str
    old_asset_number: str
    usage_category: str
    summary: str
    plate_created: str
    inventory_operator: str
    inventory_datetime: str
    asset_acquisition_date: str = ""
    has_diff: bool = False
    factory_change: bool = False
    css_class: str = ""
    plate_created_code: str = ""
    asset_photo_url: str = ""
    plate_photo_url: str = ""
    field_comparisons: tuple = ()


@dataclass
class ReconcileCounts:
    matched: int = 0
    asset_only: int = 0
    inventory_only: int = 0

    @property
    def total(self) -> int:
        return self.matched + self.asset_only + self.inventory_only


@dataclass(frozen=True)
class ListPageResult:
    management_rows: tuple[ManagementRow, ...]
    selected_management_id: str
    rows: tuple[ReconcileRow, ...]
    all_rows: tuple[ReconcileRow, ...]
    filtered_rows: tuple[ReconcileRow, ...]
    counts: ReconcileCounts
    filtered_counts: ReconcileCounts
    site_options: tuple[str, ...]
    site_filter: str
    status_filter: str
    plate_filter: str
    asset_number_filter: str
    asset_number_options: tuple[str, ...]
    page: int
    page_size: int
    total_pages: int
    sort_specs: tuple[SortSpec, ...]
    start_index: int = 0
    end_index: int = 0
    has_previous: bool = False
    has_next: bool = False
    error_message: str | None = None


class DesknetListDataGateway(Protocol):
    def list_all_records(self, access_key: str, app_id: str, fields: tuple[str, ...] | None = None) -> list[Record]: ...


ListAllRecordsFn = Callable[[str, str, tuple[str, ...] | None], list[Record]]

MANAGEMENT_APP_ID = "401"

MANAGEMENT_FIELDS = (
    "データID",
    "棚卸項目",
    "年度",
    "会社マスタ",
    "拠点マスタ",
    "資産データ",
    "棚卸データ",
)

ASSET_INVENTORY_TARGET_FIELD = "生産品番⑧コード"
ASSET_INVENTORY_TARGET_CODE = "1"

ASSET_ACQUISITION_DATE_FIELD = "取得日付"

_SHARED_RECORD_FIELDS = (
    "データID",
    "資産番号",
    "資産枝番",
    "管理部門コード",
    "管理部門名称",
    "メーカー",
    "管理者名称",
    "型番",
    "旧資産番号コード",
    "使用区分",
    "摘要",
    ASSET_INVENTORY_TARGET_FIELD,
)

ASSET_FIELDS = _SHARED_RECORD_FIELDS[:8] + (ASSET_ACQUISITION_DATE_FIELD,) + _SHARED_RECORD_FIELDS[8:]

INVENTORY_FIELDS = _SHARED_RECORD_FIELDS + (
    "棚卸日時",
    "棚卸実施者",
    "プレート作成",
    "資産写真",
    "資産プレート写真",
)

SITE_FIELDS = (
    "データID",
    "管理部門コード",
    "拠点名",
)

DISPLAY_COLUMNS: tuple[tuple[str, str], ...] = (
    ("status_label", "棚卸結果"),
    ("tone_label", "変化状況"),
    ("asset_number", "資産番号"),
    ("branch_number", "資産枝番"),
    ("site_name", "拠点名"),
    ("manufacturer", "メーカー名"),
    ("model_name", "型番"),
    ("serial_number", "シリアルNo."),
    ("asset_acquisition_date", "取得日付"),
    ("old_asset_number", "旧資産番号"),
    ("usage_category", "使用区分"),
    ("summary", "摘要"),
    ("plate_created", "プレート作成"),
    ("inventory_operator", "棚卸実施者"),
    ("inventory_datetime", "棚卸日時"),
)

STATUS_FILTER_OPTIONS: tuple[tuple[str, str], ...] = (
    ("all", "すべて"),
    ("matched", "棚卸済み"),
    ("asset_only", "未棚卸"),
    ("inventory_only", "台帳外"),
)

PLATE_FILTER_OPTIONS: tuple[tuple[str, str], ...] = (
    ("all", "すべて"),
    ("0", "プレート有"),
    ("1", "プレート作成"),
)

SORTABLE_COLUMNS: tuple[tuple[str, str], ...] = DISPLAY_COLUMNS
SORTABLE_KEYS = frozenset(key for key, _label in SORTABLE_COLUMNS)

STATUS_LABELS = {
    MatchStatus.MATCHED: "棚卸済み",
    MatchStatus.ASSET_ONLY: "未棚卸",
    MatchStatus.INVENTORY_ONLY: "台帳外",
}

TONE_LABELS = {
    RowTone.NONE: "未突合",
    RowTone.MATCH_CLEAN: "一致",
    RowTone.MATCH_DIFF: "差異",
    RowTone.MATCH_FACTORY: "拠点変更",
}

ROW_TONE_CSS = {
    RowTone.NONE: "",
    RowTone.MATCH_CLEAN: "aiv-row-clean",
    RowTone.MATCH_DIFF: "aiv-row-diff",
    RowTone.MATCH_FACTORY: "aiv-row-factory",
}

DEFAULT_PAGE_SIZE = 50
PAGE_SIZE_OPTIONS: tuple[int, ...] = (20, 50, 100, 200)
