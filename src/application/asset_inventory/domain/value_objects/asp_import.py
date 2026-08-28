"""ASP 取り込み用データ（V-306）の組み立て。

要件定義書: REQ-ASP-IMPORT-DATA-2026-001（`docs/spec/02_asp-import-data/requirements.md`）

ASP『資産／異動情報修正入力』の貼り付けレイアウトは 75 列固定であり、
本機能が値を入れるのは 資産番号(1) / 資産枝番(2) / 管理部門コード(3) / 型番(16) / 摘要(38) /
管理者コード(44) / 抽出コード１３(59) / 抽出コード１８(64) / 抽出コード１９(65) の 9 列のみ。
残り 66 列は空欄とし、ASP 側では「変更なし」として扱われる（REQ-F-003・確定事項 D-01）。
取得日付(6) は棚卸で変更しないため、差異の有無にかかわらず常に空欄とする（確定事項 D-12）。
"""

from __future__ import annotations

import csv
import enum
import io
import re
import unicodedata
from dataclasses import dataclass

from application.asset_inventory.domain.repositories.ports import MatchStatus, ReconcileRow

# 貼り付けレイアウトの列数（要件定義書 §9 付録）
ASP_COLUMN_COUNT = 75

# 値を入れる列の位置（1 始まり。REQ-F-003）
COLUMN_ASSET_NUMBER = 1
COLUMN_BRANCH_NUMBER = 2
COLUMN_DEPARTMENT_CODE = 3
COLUMN_MODEL_NUMBER = 16
COLUMN_SUMMARY = 38
COLUMN_MANAGER_CODE = 44
COLUMN_USAGE_CATEGORY_CODE = 59  # 抽出コード１３
COLUMN_MANUFACTURER_CODE = 64  # 抽出コード１８
COLUMN_OLD_ASSET_NUMBER = 65  # 抽出コード１９

# 領域長（byte。要件定義書 §9 付録）
LENGTH_ASSET_NUMBER = 12
LENGTH_BRANCH_NUMBER = 4
LENGTH_DEPARTMENT_CODE = 12
LENGTH_MODEL_NUMBER = 24
LENGTH_SUMMARY = 64
LENGTH_MANAGER_CODE = 12
LENGTH_USAGE_CATEGORY_CODE = 12
LENGTH_MANUFACTURER_CODE = 12
LENGTH_OLD_ASSET_NUMBER = 12

# 突合の比較ラベル（`row_detail.FIELD_COMPARISON_SPECS` の表示名）と ASP 列の対応。
# 判定は名称の項目で行い、出力する値は棚卸データのコード部品を使う（DD-08）。
DIFF_LABEL_SITE = "拠点名"
DIFF_LABEL_MANUFACTURER = "メーカー名"  # → 64 列目（`manufacturer_code` を出力・D-13）
DIFF_LABEL_MANAGER = "型番"  # 画面の「型番」＝ desknet's `管理者名称` → 44 列目（D-11）
DIFF_LABEL_MODEL_NUMBER = "シリアルNo."  # 画面の「シリアルNo.」＝ desknet's `型番` → 16 列目
DIFF_LABEL_OLD_ASSET_NUMBER = "旧資産番号"  # → 65 列目（D-11）
DIFF_LABEL_USAGE_CATEGORY = "使用区分"  # → 59 列目（D-11）
DIFF_LABEL_SUMMARY = "摘要"

EMPTY_MESSAGE = "取り込み対象の変更がありません。"
UNAVAILABLE_MESSAGE = "棚卸を選び直してください。"

# 警告文に列挙する資産番号の上限（違反理由ごと）
_MAX_LISTED_ASSETS = 10

# 警告文に載せる値の最大文字数。超える分は末尾を省略する（REQ-F-007）
_MAX_VALUE_CHARS = 20


SITE_UNAVAILABLE_MESSAGE = (
    "拠点マスタを取得できなかったため、管理部門コードは出力していません。"
    "拠点名の変化点は手作業で確認してください。"
)


class AspWarningKind(enum.Enum):
    """警告の種別（DD-04）。種別ごとに 1 文の警告文を組み立てる。"""

    CHECK_VIOLATION = "check_violation"  # ASP のチェック仕様に反する値
    VALUE_TRUNCATED = "value_truncated"  # 領域長を超えたため末尾を切り詰めた（D-14）
    NEWLINE_REPLACED = "newline_replaced"  # 摘要の改行を半角空白に置換した
    SITE_UNAVAILABLE = "site_unavailable"  # 拠点マスタ縮退により管理部門コードを出力できなかった


@dataclass(frozen=True)
class AspImportWarning:
    """取り込み用データ 1 件分の警告（DD-04）。

    警告は出力を止めない。利用者が貼り付ける前に値を直せるよう、理由と該当資産を伝える。
    """

    kind: AspWarningKind
    asset_label: str
    detail: str
    position: int = 0
    value: str = ""
    adjusted_value: str = ""  # 寄せたあとの値（D-14。寄せていない警告では空）

    @classmethod
    def site_unavailable(cls) -> "AspImportWarning":
        """拠点マスタ縮退の警告（出力全体に 1 件。REQ-F-009・DD-02）。"""
        return cls(
            kind=AspWarningKind.SITE_UNAVAILABLE,
            asset_label="",
            detail=SITE_UNAVAILABLE_MESSAGE,
        )

    def labelled_value(self) -> str:
        """警告文に出す「資産番号「値」」（REQ-F-007）。

        全角ハイフンや半角カナは資産番号だけ見ても判別できないため、値そのものを添える。
        値が空の違反（必須入力）は「入力が無いこと」自体が理由なので `「」` を付けない。
        寄せた警告（D-14）は、黙って値を変えたと受け取られないよう変換前→変換後を並べる。
        """
        if not self.value:
            return self.asset_label
        listed = f"{self.asset_label}「{_abbreviated(self.value)}」"
        if self.adjusted_value:
            listed += f"→「{_abbreviated(self.adjusted_value)}」"
        return listed


@dataclass(frozen=True)
class AspImportWarnings:
    """警告のファーストクラスコレクション（DD-04）。"""

    warnings: tuple[AspImportWarning, ...] = ()

    def __len__(self) -> int:
        return len(self.warnings)

    def of_kind(self, kind: AspWarningKind) -> "AspImportWarnings":
        """種別で絞り込む。"""
        return AspImportWarnings(tuple(w for w in self.warnings if w.kind is kind))

    def asset_labels(self) -> tuple[str, ...]:
        """該当資産のラベルを重複なく返す（出現順を保つ）。"""
        labels: list[str] = []
        for warning in self.warnings:
            if warning.asset_label and warning.asset_label not in labels:
                labels.append(warning.asset_label)
        return tuple(labels)

    def merged(self, other: "AspImportWarnings") -> "AspImportWarnings":
        """2 つのコレクションを連結する。"""
        return AspImportWarnings(self.warnings + other.warnings)

    def with_site_unavailable(self) -> "AspImportWarnings":
        """拠点マスタ縮退の警告を 1 件だけ加える（重ねて呼んでも増えない）。"""
        if self.of_kind(AspWarningKind.SITE_UNAVAILABLE):
            return self
        return AspImportWarnings(self.warnings + (AspImportWarning.site_unavailable(),))

    def message(self) -> str:
        """画面表示用の警告文を組み立てる（REQ-F-007）。警告が無ければ空文字。

        種別ごとにブロックを作り、複数あれば改行で連結する（C-15）。
        チェック仕様違反は見出し 1 行のあとに**違反理由ごとの明細行**を並べる。
        資産番号だけを列挙しても「どの列をどう直すか」が分からないためである。
        ブロックの順は 違反 → 切り捨て → 改行置換 → 拠点マスタ縮退（D-14・D-15）。
        直さなければならないものを先に、こちらが直したものを後に読ませる。
        **半角変換は警告に出さない**（D-15・DD-11）。書式を合わせるだけで値の情報が
        失われず、毎回通知すると本当に確認が要る指摘（違反・切り捨て）が埋もれるため。
        """
        lines: list[str] = []

        violations = self.of_kind(AspWarningKind.CHECK_VIOLATION)
        if violations:
            lines.append(
                f"ASP のチェック仕様に反する値が {len(violations.asset_labels())} 件あります。"
                "値を直してから貼り付けてください。"
            )
            lines.extend(violations._detail_lines())

        truncated = self.of_kind(AspWarningKind.VALUE_TRUNCATED)
        if truncated:
            lines.append(
                f"領域長を超えたため末尾を切り詰めた値が {len(truncated.asset_labels())} 件あります。"
                "内容を確認してください。"
            )
            lines.extend(truncated._detail_lines())

        replaced = self.of_kind(AspWarningKind.NEWLINE_REPLACED)
        if replaced:
            lines.append(
                f"摘要の改行を半角空白に置き換えた行が {len(replaced.asset_labels())} 件あります"
                f"（資産番号: {replaced._listed_labels()}）。内容を確認してください。"
            )

        if self.of_kind(AspWarningKind.SITE_UNAVAILABLE):
            lines.append(SITE_UNAVAILABLE_MESSAGE)

        return "\n".join(lines)

    def _detail_lines(self) -> list[str]:
        """違反理由ごとに明細行を 1 行ずつ作る（REQ-F-007）。

        同じ理由の資産をまとめることで、利用者が「対処の単位」で読めるようにする。
        行の並びは ASP 上の列位置の昇順とし、同一列内は検査の順に従う。
        出力のたびに順序が変わると差分が読めなくなるためである。
        """
        grouped: dict[str, list[AspImportWarning]] = {}
        sort_keys: dict[str, tuple[int, int]] = {}
        for index, warning in enumerate(self.warnings):
            if warning.detail not in grouped:
                grouped[warning.detail] = []
                sort_keys[warning.detail] = (warning.position, index)
            grouped[warning.detail].append(warning)

        return [
            f"・{detail} — {_listed_assets(grouped[detail])}"
            for detail in sorted(grouped, key=lambda detail: sort_keys[detail])
        ]

    def _listed_labels(self) -> str:
        """資産番号の列挙。10 件を上限とし、超過分は「ほか N 件」に丸める。"""
        labels = self.asset_labels()
        listed = "、".join(labels[:_MAX_LISTED_ASSETS])
        if len(labels) > _MAX_LISTED_ASSETS:
            listed += f" ほか {len(labels) - _MAX_LISTED_ASSETS} 件"
        return listed


@dataclass(frozen=True)
class NormalizedValue:
    """ASP の書式へ整形した値と、書き換えたかどうか（REQ-F-006・DD-03）。

    整形の対象ごとにクラスメソッドを分けることで、資産枝番以外にゼロ埋めが
    漏れ出さないようにする。
    """

    value: str
    newline_replaced: bool = False

    @classmethod
    def trimmed(cls, raw: str) -> "NormalizedValue":
        """資産番号・管理部門コード・シリアルNo.・追加 4 コード: 前後の空白を除くだけ（ゼロ埋めしない）。"""
        return cls((raw or "").strip())

    @classmethod
    def branch_number(cls, raw: str) -> "NormalizedValue":
        """資産枝番: 数字のみの場合に限り 4 桁ゼロ埋め。

        空欄・数字以外はそのまま返し、チェック仕様側（`O`・`I`）で警告する。
        5 桁以上の数字も切り詰めず、領域長の違反として警告する。
        """
        cleaned = (raw or "").strip()
        if cleaned.isdigit():
            # zfill は桁数が足りている値をそのまま返すため、5 桁以上は切り詰められない
            return cls(cleaned.zfill(LENGTH_BRANCH_NUMBER))
        return cls(cleaned)

    @classmethod
    def summary(cls, raw: str) -> "NormalizedValue":
        """摘要: 前後の空白を除き、改行を半角空白 1 つに置換する（確定事項 D-08）。

        CRLF → LF → CR の順に置換する。順序を入れ替えると CRLF が空白 2 つになる。
        """
        cleaned = (raw or "").strip()
        replaced = cleaned.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
        return cls(replaced, newline_replaced=replaced != cleaned)


@dataclass(frozen=True)
class AdjustedValue:
    """ASP の書式へ寄せた値と、寄せた内容（REQ-F-006・D-14・DD-10）。

    `NormalizedValue` が「desknet's の値を ASP の書式に整える」のに対し、
    こちらは「ASP のチェック仕様に合わせて値そのものを直す」。
    直した事実を持ち回ることで、黙って値を変えたことにならないようにする。
    """

    original: str
    value: str
    half_width_converted: bool = False  # 変換の事実は保持するが警告にはしない（D-15・DD-11）
    truncated: bool = False


# チェック仕様の記号（要件定義書 §9 付録。ASP の入力仕様書に準じる）
CHECK_REQUIRED = "O"  # 必須入力
CHECK_HALF_WIDTH = "M"  # 半角英数記号
CHECK_INTEGER = "I"  # 整数
CHECK_NUMERIC = "N"  # 数値
CHECK_DATE = "D"  # 日付
CHECK_FULL_WIDTH = "P"  # 全角可

_DATE_PATTERN = re.compile(r"\A\d{4}([/-]?)\d{2}\1\d{2}\Z")


@dataclass(frozen=True)
class AspFieldCheck:
    """ASP の 1 列分のチェック仕様（V-310・REQ-F-007）。

    列ごとのチェック記号と領域長をまとめて持ち、値がそれに反するかを自分で判定する。
    出力そのものは止めず、警告として利用者に返すための材料を作る。
    """

    position: int
    label: str
    checks: frozenset[str]
    max_bytes: int
    truncatable: bool = True  # 領域長超過時に末尾を切り捨てるか（D-14）

    @property
    def subject(self) -> str:
        """違反理由の主語。ASP のどのセルを見ればよいかを示す（REQ-F-007）。"""
        return f"{self.label}（{self.position} 列目）"

    def adjusted(self, value: str) -> AdjustedValue:
        """値を ASP の書式へ寄せる（REQ-F-006・D-14・DD-10）。

        半角変換 → 領域長の切り捨て の順に適用する。変換で byte 数が減るため、
        順を入れ替えると本来切り捨てずに済む値まで切り詰めてしまう。
        `violations()` はここで寄せたあとの値に対して呼ぶ（同じ事実を二重に判定しない）。
        """
        if not value:
            return AdjustedValue(original=value, value=value)

        converted = _to_half_width(value) if CHECK_HALF_WIDTH in self.checks else value
        cut = _truncated(converted, self.max_bytes) if self.truncatable else converted
        return AdjustedValue(
            original=value,
            value=cut,
            half_width_converted=converted != value,
            truncated=cut != converted,
        )

    def violations(self, value: str) -> tuple[str, ...]:
        """チェック仕様に反する理由をすべて返す（REQ-F-007）。反しなければ空タプル。

        値が空の場合は必須入力（`O`）だけを見る。空欄に対して書式や領域長を
        重ねて警告しても、利用者が直すべき箇所は「入力すること」ひとつだからである。
        """
        if not value:
            return (f"{self.subject}が空です",) if CHECK_REQUIRED in self.checks else ()

        reasons: list[str] = []
        if CHECK_HALF_WIDTH in self.checks and not _is_half_width(value):
            reasons.append(f"{self.subject}に半角英数記号以外が含まれます")
        if CHECK_INTEGER in self.checks and not value.isdigit():
            reasons.append(f"{self.subject}が数字ではありません")
        if CHECK_NUMERIC in self.checks and not _is_numeric(value):
            reasons.append(f"{self.subject}が数値ではありません")
        if CHECK_DATE in self.checks and not _DATE_PATTERN.match(value):
            reasons.append(f"{self.subject}が日付ではありません")
        # チェック P（全角可）は文字種を問わないため、領域長のみを見る
        if _byte_length(value) > self.max_bytes:
            reasons.append(f"{self.subject}が {self.max_bytes} byte を超えています")
        return tuple(reasons)


# 値を入れる 9 列のチェック仕様（キー＝列位置。要件定義書 §9 付録）
# `position` をキーに組み立てるため、キーと属性は必ず一致する。
ASP_FIELD_CHECKS: dict[int, AspFieldCheck] = {
    check.position: check
    for check in (
        AspFieldCheck(
            position=COLUMN_ASSET_NUMBER,
            label="資産番号",
            checks=frozenset({CHECK_REQUIRED, CHECK_HALF_WIDTH}),
            max_bytes=LENGTH_ASSET_NUMBER,
            # 更新対象の資産を特定するキーのため切り詰めない（別の資産を書き換えてしまう）
            truncatable=False,
        ),
        AspFieldCheck(
            position=COLUMN_BRANCH_NUMBER,
            label="資産枝番",
            checks=frozenset({CHECK_REQUIRED, CHECK_INTEGER}),
            max_bytes=LENGTH_BRANCH_NUMBER,
            truncatable=False,  # 資産番号と同じ理由（D-14）
        ),
        AspFieldCheck(
            position=COLUMN_DEPARTMENT_CODE,
            label="管理部門コード",
            checks=frozenset({CHECK_HALF_WIDTH}),
            max_bytes=LENGTH_DEPARTMENT_CODE,
        ),
        AspFieldCheck(
            position=COLUMN_MODEL_NUMBER,
            label="型番",
            checks=frozenset({CHECK_HALF_WIDTH}),
            max_bytes=LENGTH_MODEL_NUMBER,
        ),
        AspFieldCheck(
            position=COLUMN_SUMMARY,
            label="摘要",
            checks=frozenset({CHECK_FULL_WIDTH}),
            max_bytes=LENGTH_SUMMARY,
        ),
        AspFieldCheck(
            position=COLUMN_MANAGER_CODE,
            label="管理者コード",
            checks=frozenset({CHECK_HALF_WIDTH}),
            max_bytes=LENGTH_MANAGER_CODE,
        ),
        AspFieldCheck(
            position=COLUMN_USAGE_CATEGORY_CODE,
            label="使用区分コード",
            checks=frozenset({CHECK_HALF_WIDTH}),
            max_bytes=LENGTH_USAGE_CATEGORY_CODE,
        ),
        AspFieldCheck(
            position=COLUMN_MANUFACTURER_CODE,
            label="メーカーコード",
            checks=frozenset({CHECK_HALF_WIDTH}),
            max_bytes=LENGTH_MANUFACTURER_CODE,
        ),
        AspFieldCheck(
            position=COLUMN_OLD_ASSET_NUMBER,
            label="旧資産番号コード",
            checks=frozenset({CHECK_HALF_WIDTH}),
            max_bytes=LENGTH_OLD_ASSET_NUMBER,
        ),
    )
}


@dataclass(frozen=True)
class DepartmentCode:
    """管理部門コード（V-311）。拠点を ASP 上で識別するコード（REQ-F-003）。

    独立した型を設けるのはチェック仕様（`M`・12 byte）を型に結びつけるためであり、
    判定そのものは `ASP_FIELD_CHECKS` に委譲して二重に持たない。
    """

    value: str

    @classmethod
    def from_site_code(cls, site_code: str) -> "DepartmentCode":
        """棚卸データの拠点コードから生成する。前後の空白は除く（REQ-F-006）。"""
        return cls(NormalizedValue.trimmed(site_code).value)

    def violations(self) -> tuple[str, ...]:
        """チェック仕様に反する理由を返す（REQ-F-007）。空欄は違反にしない（`O` 対象外）。"""
        return ASP_FIELD_CHECKS[COLUMN_DEPARTMENT_CODE].violations(self.value)


def _is_numeric(value: str) -> bool:
    """チェック N（数値）: 符号と小数点を許した数値表記かどうか。"""
    try:
        float(value)
    except ValueError:
        return False
    return True


class AspPasteLayout:
    """ASP『資産／異動情報修正入力』の貼り付けレイアウト（V-309）。

    列の並びと総列数（75 列固定）を表す。全 75 列の一覧は要件定義書 §9 付録を正とし、
    ここでは値を入れる 9 列の位置だけを持つ（二重管理を避けるため）。
    """

    COLUMN_COUNT = ASP_COLUMN_COUNT
    ASSET_NUMBER = COLUMN_ASSET_NUMBER
    BRANCH_NUMBER = COLUMN_BRANCH_NUMBER
    DEPARTMENT_CODE = COLUMN_DEPARTMENT_CODE
    MODEL_NUMBER = COLUMN_MODEL_NUMBER
    SUMMARY = COLUMN_SUMMARY
    MANAGER_CODE = COLUMN_MANAGER_CODE
    USAGE_CATEGORY_CODE = COLUMN_USAGE_CATEGORY_CODE
    MANUFACTURER_CODE = COLUMN_MANUFACTURER_CODE
    OLD_ASSET_NUMBER = COLUMN_OLD_ASSET_NUMBER

    @classmethod
    def blank_columns(cls) -> tuple[str, ...]:
        """75 個の空文字を返す。ここに値を差し込んで 1 行を作る（REQ-F-003・確定事項 D-01）。"""
        return ("",) * cls.COLUMN_COUNT


@dataclass(frozen=True)
class AspImportRow:
    """取り込み用データの 1 行（V-306 の構成要素）。"""

    columns: tuple[str, ...]
    asset_label: str
    warnings: AspImportWarnings = AspImportWarnings()

    @classmethod
    def from_reconcile_row(cls, row: ReconcileRow) -> "AspImportRow":
        """突合結果の 1 行から組み立てる（REQ-F-003・REQ-F-004・REQ-F-006・REQ-F-007）。

        差異の判定は既存の変化点判定（A-301）の結果を読むだけとし、比較をやり直さない。
        """
        diffs = _diff_labels(row)
        values = AspPasteLayout.blank_columns()
        columns = list(values)

        # 必須入力項目（チェック O）は差異の有無にかかわらず常に出力する
        asset_number = NormalizedValue.trimmed(row.asset_number)
        branch_number = NormalizedValue.branch_number(row.branch_number)
        columns[AspPasteLayout.ASSET_NUMBER - 1] = asset_number.value
        columns[AspPasteLayout.BRANCH_NUMBER - 1] = branch_number.value

        summary = NormalizedValue.summary(row.summary) if DIFF_LABEL_SUMMARY in diffs else None
        if DIFF_LABEL_SITE in diffs:
            columns[AspPasteLayout.DEPARTMENT_CODE - 1] = DepartmentCode.from_site_code(
                row.site_code
            ).value
        if DIFF_LABEL_MODEL_NUMBER in diffs:
            columns[AspPasteLayout.MODEL_NUMBER - 1] = NormalizedValue.trimmed(
                row.serial_number
            ).value
        # 以下は名称で差異を判定し、コード部品の値を出力する（DD-08）
        if DIFF_LABEL_MANAGER in diffs:
            columns[AspPasteLayout.MANAGER_CODE - 1] = NormalizedValue.trimmed(
                row.manager_code
            ).value
        if DIFF_LABEL_USAGE_CATEGORY in diffs:
            columns[AspPasteLayout.USAGE_CATEGORY_CODE - 1] = NormalizedValue.trimmed(
                row.usage_category_code
            ).value
        if DIFF_LABEL_MANUFACTURER in diffs:
            columns[AspPasteLayout.MANUFACTURER_CODE - 1] = NormalizedValue.trimmed(
                row.manufacturer_code
            ).value
        if DIFF_LABEL_OLD_ASSET_NUMBER in diffs:
            columns[AspPasteLayout.OLD_ASSET_NUMBER - 1] = NormalizedValue.trimmed(
                row.old_asset_number
            ).value
        if summary is not None:
            columns[AspPasteLayout.SUMMARY - 1] = summary.value

        # 出力する値を ASP の書式へ寄せてから検査する（D-14・DD-10）
        adjusted = _adjust_columns(tuple(columns))
        adjusted_columns = tuple(
            adjusted[position].value if position in adjusted else value
            for position, value in enumerate(columns, start=1)
        )

        asset_label = _build_asset_label(
            adjusted_columns[AspPasteLayout.ASSET_NUMBER - 1],
            adjusted_columns[AspPasteLayout.BRANCH_NUMBER - 1],
        )
        return cls(
            columns=adjusted_columns,
            asset_label=asset_label,
            warnings=_build_row_warnings(adjusted_columns, asset_label, summary, adjusted),
        )


@dataclass(frozen=True)
class AspImportRows:
    """取り込み用データ（V-306）。`AspImportRow` のファーストクラスコレクション。"""

    rows: tuple[AspImportRow, ...] = ()
    site_warning: bool = False

    @classmethod
    def from_rows(
        cls, rows: tuple[AspImportRow, ...], *, site_warning: bool = False
    ) -> "AspImportRows":
        """行を束ねる。拠点マスタ縮退時は管理部門コードを出力しない（REQ-F-009・DD-02）。"""
        if site_warning:
            rows = tuple(_without_department_code(row) for row in rows)
        return cls(rows=rows, site_warning=site_warning)

    def __len__(self) -> int:
        return len(self.rows)

    def render_csv(self) -> bytes:
        """ヘッダー行なし・75 列固定・CRLF・UTF-8(BOM 付き) の CSV を返す（REQ-F-005）。"""
        if not self.rows:
            return b""
        buffer = io.StringIO()
        writer = csv.writer(buffer, lineterminator="\r\n")
        for row in self.rows:
            writer.writerow(row.columns)
        return ("\ufeff" + buffer.getvalue()).encode("utf-8")

    def warnings(self) -> AspImportWarnings:
        """全行の警告を連結して返す（REQ-F-007）。拠点マスタ縮退は出力全体で 1 件（DD-04）。"""
        collected = AspImportWarnings(
            tuple(warning for row in self.rows for warning in row.warnings.warnings)
        )
        return collected.with_site_unavailable() if self.site_warning else collected


def _without_department_code(row: AspImportRow) -> AspImportRow:
    """管理部門コードの列を空欄にした行を返す（拠点マスタ縮退時・REQ-F-009）。"""
    position = AspPasteLayout.DEPARTMENT_CODE - 1
    if not row.columns[position]:
        return row
    columns = list(row.columns)
    columns[position] = ""
    return AspImportRow(
        columns=tuple(columns), asset_label=row.asset_label, warnings=row.warnings
    )


@dataclass(frozen=True)
class AmendmentRows:
    """修正対象行（V-307）。`ReconcileRow` のファーストクラスコレクション。"""

    rows: tuple[ReconcileRow, ...] = ()

    @classmethod
    def select_from(cls, rows: tuple[ReconcileRow, ...]) -> "AmendmentRows":
        """棚卸済み かつ 変化点あり の行だけを入力順のまま抽出する（REQ-F-002）。

        未棚卸・台帳外・変化点なしの行は対象外。行数の上限は設けない（確定事項 D-10）。
        """
        return cls(
            tuple(
                row for row in rows if row.match_status == MatchStatus.MATCHED and row.has_diff
            )
        )

    def __len__(self) -> int:
        return len(self.rows)

    def is_empty(self) -> bool:
        """0 件かどうか（REQ-F-008 の分岐に使う）。"""
        return not self.rows

    def count(self) -> int:
        """件数（応答ヘッダーの行数に使う）。"""
        return len(self.rows)

    def to_import_rows(self, *, site_warning: bool = False) -> AspImportRows:
        """各行を取り込み用データの 1 行に変換する（REQ-F-003）。"""
        return AspImportRows.from_rows(
            tuple(AspImportRow.from_reconcile_row(row) for row in self.rows),
            site_warning=site_warning,
        )


def _build_asset_label(asset_number: str, branch_number: str) -> str:
    """警告表示に使う識別ラベル。資産枝番が空なら資産番号のみ（設計 §4.2(e)）。"""
    if not asset_number:
        return "(資産番号なし)"
    return f"{asset_number}-{branch_number}" if branch_number else asset_number


def _adjust_columns(columns: tuple[str, ...]) -> dict[int, AdjustedValue]:
    """9 列の値を ASP の書式へ寄せる（D-14・DD-10）。キーは列位置。"""
    return {
        position: check.adjusted(columns[position - 1])
        for position, check in ASP_FIELD_CHECKS.items()
    }


def _build_row_warnings(
    columns: tuple[str, ...],
    asset_label: str,
    summary: NormalizedValue | None,
    adjusted: dict[int, AdjustedValue] | None = None,
) -> AspImportWarnings:
    """1 行分の警告を組み立てる（REQ-F-006・REQ-F-007・DD-04）。

    `columns` は寄せたあとの値。違反の判定も寄せたあとの値に対して行う（DD-10）。
    """
    warnings: list[AspImportWarning] = [
        AspImportWarning(
            kind=AspWarningKind.CHECK_VIOLATION,
            asset_label=asset_label,
            detail=detail,
            position=position,
            value=columns[position - 1],
        )
        for position, check in ASP_FIELD_CHECKS.items()
        for detail in check.violations(columns[position - 1])
    ]
    for position, value in (adjusted or {}).items():
        check = ASP_FIELD_CHECKS[position]
        if value.truncated:
            warnings.append(
                AspImportWarning(
                    kind=AspWarningKind.VALUE_TRUNCATED,
                    asset_label=asset_label,
                    detail=f"{check.subject}を {check.max_bytes} byte に切り詰めました",
                    position=position,
                    value=value.original,
                    adjusted_value=value.value,
                )
            )
    if summary is not None and summary.newline_replaced:
        warnings.append(
            AspImportWarning(
                kind=AspWarningKind.NEWLINE_REPLACED,
                asset_label=asset_label,
                detail="摘要の改行を半角空白に置き換えました",
                position=COLUMN_SUMMARY,
            )
        )
    return AspImportWarnings(tuple(warnings))


def _diff_labels(row: ReconcileRow) -> frozenset[str]:
    return frozenset(
        item.label for item in (row.field_comparisons or ()) if getattr(item, "is_diff", False)
    )


def _clean(value: str) -> str:
    return (value or "").strip()


def _byte_length(value: str) -> int:
    """ASP の領域長はバイト数で規定されるため cp932 換算で数える（全角 2 byte）。"""
    try:
        return len(value.encode("cp932"))
    except UnicodeEncodeError:
        # cp932 で表せない文字が含まれる場合は安全側（多めのバイト数）で評価する
        return len(value.encode("utf-8"))


def _abbreviated(value: str) -> str:
    """警告文に載せる値。長すぎると画面が読めなくなるため末尾を省略する（REQ-F-007）。"""
    if len(value) <= _MAX_VALUE_CHARS:
        return value
    return value[:_MAX_VALUE_CHARS] + "…"


def _listed_assets(warnings: list[AspImportWarning]) -> str:
    """違反理由 1 件分の該当資産の列挙。10 件を上限とし、超過分は「ほか N 件」に丸める。"""
    listed = "、".join(warning.labelled_value() for warning in warnings[:_MAX_LISTED_ASSETS])
    if len(warnings) > _MAX_LISTED_ASSETS:
        listed += f" ほか {len(warnings) - _MAX_LISTED_ASSETS} 件"
    return listed


def _is_half_width(value: str) -> bool:
    """チェック M（半角英数記号）: ASCII の印字可能文字のみを許容する。"""
    return all("\x20" <= char <= "\x7e" for char in value)


# NFKC で半角にならない記号の写像（D-14・DD-10 段 2）
_HALF_WIDTH_ALWAYS = str.maketrans(
    {
        "\u2010": "-",  # ‐ HYPHEN
        "\u2011": "-",  # ‑ NON-BREAKING HYPHEN
        "\u2012": "-",  # ‒ FIGURE DASH
        "\u2013": "-",  # – EN DASH
        "\u2014": "-",  # — EM DASH
        "\u2015": "-",  # ― HORIZONTAL BAR
        "\u2212": "-",  # − MINUS SIGN
        "\u2018": "'",  # ‘
        "\u2019": "'",  # ’
        "\u201c": '"',  # “
        "\u201d": '"',  # ”
    }
)

# 長音記号。日本語を含まない値に限って半角ハイフンへ寄せる（D-14・DD-10 段 3）
_PROLONGED_MARKS = str.maketrans({"\u30fc": "-", "\uff70": "-"})

# ひらがな・カタカナ・漢字。長音記号（U+30FC）自身は含めない
_JAPANESE_PATTERN = re.compile("[\u3041-\u309f\u30a1-\u30fb\u30fd-\u30ff\u4e00-\u9fff]")


def _to_half_width(value: str) -> str:
    """チェック M の列の値を半角へ寄せる（REQ-F-006・D-14・DD-10）。

    NFKC は全角英数字・全角空白は直すが、長音記号やダッシュ類は直さない。
    そこで写像を重ねる。ただし `モーター` のようなカナ語の長音まで `-` にすると
    日本語が壊れるため、かな・カナ・漢字が残る値では長音記号に触らない。
    """
    converted = unicodedata.normalize("NFKC", value).translate(_HALF_WIDTH_ALWAYS)
    if _JAPANESE_PATTERN.search(converted):
        return converted
    return converted.translate(_PROLONGED_MARKS)


def _truncated(value: str, max_bytes: int) -> str:
    """領域長を超えた分を末尾から切り捨てる（REQ-F-006・D-14・DD-10）。

    先頭から 1 文字ずつ積み上げ、加えると超える文字の手前で打ち切る。
    byte 数で機械的に切ると全角 1 文字が分断され、ASP 側で文字化けするためである。
    """
    if _byte_length(value) <= max_bytes:
        return value

    kept: list[str] = []
    used = 0
    for char in value:
        size = _byte_length(char)
        if used + size > max_bytes:
            break
        kept.append(char)
        used += size
    return "".join(kept)
