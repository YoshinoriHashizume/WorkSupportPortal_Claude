from __future__ import annotations

from application.asset_inventory.domain.repositories.ports import MatchStatus, ReconcileRow, RowTone
from application.asset_inventory.domain.value_objects.asp_import import (
    ASP_COLUMN_COUNT,
    ASP_FIELD_CHECKS,
    COLUMN_ASSET_NUMBER,
    COLUMN_BRANCH_NUMBER,
    COLUMN_DEPARTMENT_CODE,
    COLUMN_MANAGER_CODE,
    COLUMN_MANUFACTURER_CODE,
    COLUMN_MODEL_NUMBER,
    COLUMN_OLD_ASSET_NUMBER,
    COLUMN_SUMMARY,
    COLUMN_USAGE_CATEGORY_CODE,
    EMPTY_MESSAGE,
    UNAVAILABLE_MESSAGE,
    AmendmentRows,
    AspImportRow,
    AspImportRows,
    AspImportWarning,
    AspImportWarnings,
    AspPasteLayout,
    AspWarningKind,
    DepartmentCode,
    NormalizedValue,
)
from application.asset_inventory.domain.value_objects.row_detail import FieldComparisonItem


def _comparisons(**diffs: bool) -> tuple[FieldComparisonItem, ...]:
    """ラベル -> 差異ありかどうか。指定のないラベルは差異なしとする。"""
    labels = (
        "資産番号",
        "資産枝番",
        "拠点名",
        "メーカー名",
        "型番",
        "シリアルNo.",
        "旧資産番号",
        "使用区分",
        "摘要",
    )
    alias = {
        "site": "拠点名",
        "maker": "メーカー名",
        "model": "型番",
        "serial": "シリアルNo.",
        "old": "旧資産番号",
        "usage": "使用区分",
        "summary": "摘要",
    }
    diff_labels = {alias[key] for key in diffs if diffs[key]}
    return tuple(
        FieldComparisonItem(
            label=label,
            asset_value="A" if label in diff_labels else "same",
            inventory_value="B" if label in diff_labels else "same",
            is_diff=label in diff_labels,
        )
        for label in labels
    )


def _comparisons_all_diff() -> tuple[FieldComparisonItem, ...]:
    """変化点判定の 7 項目すべてに差異がある状態（9 列すべてに値が入る行を作る）。"""
    return _comparisons(
        site=True, maker=True, model=True, serial=True, old=True, usage=True, summary=True
    )


def _row(
    *,
    status: MatchStatus = MatchStatus.MATCHED,
    tone: RowTone = RowTone.MATCH_DIFF,
    has_diff: bool = True,
    asset_number: str = "5262",
    branch_number: str = "1",
    site_code: str = "001",
    serial_number: str = "SN-100",
    summary: str = "摘要テキスト",
    manager_code: str = "MGR1",
    usage_category_code: str = "U1",
    manufacturer_code: str = "MK1",
    old_asset_number: str = "OLD1",
    comparisons: tuple[FieldComparisonItem, ...] | None = None,
) -> ReconcileRow:
    return ReconcileRow(
        match_status=status,
        row_tone=tone,
        status_label="棚卸済み",
        tone_label="差異",
        asset_number=asset_number,
        branch_number=branch_number,
        site_name="宮崎工場",
        manufacturer="M",
        model_name="MODEL",
        serial_number=serial_number,
        old_asset_number=old_asset_number,
        usage_category="使用",
        summary=summary,
        plate_created="プレート有",
        plate_created_code="0",
        inventory_operator="担当",
        inventory_datetime="2026/01/16 18:46:01",
        has_diff=has_diff,
        site_code=site_code,
        manager_code=manager_code,
        usage_category_code=usage_category_code,
        manufacturer_code=manufacturer_code,
        field_comparisons=comparisons if comparisons is not None else _comparisons(summary=True),
    )


def _columns_of(row: ReconcileRow) -> tuple[str, ...]:
    """突合結果の 1 行から 75 列を組み立てる。"""
    return AspImportRow.from_reconcile_row(row).columns


# --- REQ-F-002 出力対象行 -------------------------------------------------


def test_TC_AIV_ASP_001_selects_matched_rows_with_diff():
    """棚卸済みかつ変化点のある行だけが修正対象行になる（REQ-F-002）。"""
    target = _row()
    clean = _row(tone=RowTone.MATCH_CLEAN, has_diff=False, comparisons=_comparisons())
    asset_only = _row(status=MatchStatus.ASSET_ONLY, has_diff=False)
    inventory_only = _row(status=MatchStatus.INVENTORY_ONLY, has_diff=False)

    selected = AmendmentRows.select_from((target, clean, asset_only, inventory_only)).rows

    assert selected == (target,)


def test_TC_AIV_ASP_002_factory_change_rows_are_selected():
    """変化状況が拠点変更の行も修正対象行に含む（REQ-F-002）。"""
    factory = _row(tone=RowTone.MATCH_FACTORY, comparisons=_comparisons(site=True))
    assert AmendmentRows.select_from((factory,)).rows == (factory,)


def test_TC_AIV_ASP_003_rows_without_mapped_column_are_still_selected():
    """ASP に対応列のない項目だけの差異でも行自体は出力する（REQ-F-004）。"""
    row = _row(comparisons=_comparisons(maker=True, usage=True))
    assert AmendmentRows.select_from((row,)).rows == (row,)


# --- REQ-F-003 出力する列 -------------------------------------------------


def test_TC_AIV_ASP_010_always_75_columns():
    """列数は 75 列固定（REQ-F-003・REQ-F-005）。"""
    columns = _columns_of(_row())
    assert len(columns) == ASP_COLUMN_COUNT == 75


def test_TC_AIV_ASP_011_asset_number_and_branch_always_output():
    """資産番号・資産枝番は差異の有無にかかわらず常に出力する（REQ-F-004）。"""
    columns = _columns_of(_row(comparisons=_comparisons(maker=True)))
    assert columns[0] == "5262"
    assert columns[COLUMN_BRANCH_NUMBER - 1] == "0001"


def test_TC_AIV_ASP_012_branch_number_zero_padded():
    """資産枝番は 4 桁ゼロ埋め（REQ-F-006）。"""
    assert _columns_of(_row(branch_number="12"))[1] == "0012"
    assert _columns_of(_row(branch_number="0034"))[1] == "0034"


def test_TC_AIV_ASP_013_department_code_only_when_site_differs():
    """管理部門コードは拠点名に差異がある場合のみ出力する（REQ-F-003）。"""
    with_diff = _columns_of(_row(comparisons=_comparisons(site=True)))
    without_diff = _columns_of(_row(comparisons=_comparisons(summary=True)))
    assert with_diff[COLUMN_DEPARTMENT_CODE - 1] == "001"
    assert without_diff[COLUMN_DEPARTMENT_CODE - 1] == ""


def test_TC_AIV_ASP_014_model_number_uses_serial_number_field():
    """ASP 16 列目「型番」は画面「シリアルNo.」の値（desknet's 型番フィールド）を出力する。"""
    with_diff = _columns_of(_row(comparisons=_comparisons(serial=True)))
    without_diff = _columns_of(_row(comparisons=_comparisons(summary=True)))
    assert with_diff[COLUMN_MODEL_NUMBER - 1] == "SN-100"
    assert without_diff[COLUMN_MODEL_NUMBER - 1] == ""


def test_TC_AIV_ASP_015_model_name_diff_goes_to_manager_code_column():
    """画面「型番」の差異は 16 列目ではなく 44 列目に出力する（REQ-F-004・D-07・D-11）。"""
    columns = _columns_of(_row(comparisons=_comparisons(model=True)))
    assert columns[COLUMN_MODEL_NUMBER - 1] == ""
    assert columns[COLUMN_MANAGER_CODE - 1] == "MGR1"


def test_TC_AIV_ASP_016_summary_only_when_summary_differs():
    """摘要は 38 列目に、差異がある場合のみ出力する（REQ-F-003）。"""
    with_diff = _columns_of(_row(comparisons=_comparisons(summary=True)))
    without_diff = _columns_of(_row(comparisons=_comparisons(site=True)))
    assert with_diff[COLUMN_SUMMARY - 1] == "摘要テキスト"
    assert without_diff[COLUMN_SUMMARY - 1] == ""


def test_TC_AIV_ASP_017_other_columns_are_blank():
    """値を入れるのは 9 列のみで、残り 66 列は空欄（REQ-F-003）。"""
    columns = _columns_of(_row(comparisons=_comparisons_all_diff()))
    filled = {index + 1 for index, value in enumerate(columns) if value}
    assert filled == {
        1,
        2,
        COLUMN_DEPARTMENT_CODE,
        COLUMN_MODEL_NUMBER,
        COLUMN_SUMMARY,
        COLUMN_MANAGER_CODE,
        COLUMN_USAGE_CATEGORY_CODE,
        COLUMN_MANUFACTURER_CODE,
        COLUMN_OLD_ASSET_NUMBER,
    }


def test_TC_AIV_ASP_018_values_are_trimmed():
    """値は前後の空白を除いて出力する（REQ-F-006）。"""
    row = _row(asset_number=" 5262 ", summary=" 摘要 ", comparisons=_comparisons(summary=True))
    columns = _columns_of(row)
    assert columns[0] == "5262"
    assert columns[COLUMN_SUMMARY - 1] == "摘要"


def test_TC_AIV_ASP_080_manager_code_only_when_model_name_differs():
    """管理者コードは画面「型番」に差異がある場合のみ 44 列目に出力する（D-11・C-18）。"""
    with_diff = _columns_of(_row(comparisons=_comparisons(model=True)))
    without_diff = _columns_of(_row(comparisons=_comparisons(summary=True)))
    assert with_diff[COLUMN_MANAGER_CODE - 1] == "MGR1"
    assert without_diff[COLUMN_MANAGER_CODE - 1] == ""


def test_TC_AIV_ASP_081_usage_category_code_only_when_usage_differs():
    """使用区分コードは使用区分に差異がある場合のみ 59 列目に出力する（D-11・C-19）。"""
    with_diff = _columns_of(_row(comparisons=_comparisons(usage=True)))
    without_diff = _columns_of(_row(comparisons=_comparisons(summary=True)))
    assert with_diff[COLUMN_USAGE_CATEGORY_CODE - 1] == "U1"
    assert without_diff[COLUMN_USAGE_CATEGORY_CODE - 1] == ""


def test_TC_AIV_ASP_082_manufacturer_code_only_when_manufacturer_differs():
    """メーカーコードはメーカー名に差異がある場合のみ 64 列目に出力する（D-13・C-22）。"""
    with_diff = _columns_of(_row(comparisons=_comparisons(maker=True)))
    without_diff = _columns_of(_row(comparisons=_comparisons(summary=True)))
    assert with_diff[COLUMN_MANUFACTURER_CODE - 1] == "MK1"
    assert without_diff[COLUMN_MANUFACTURER_CODE - 1] == ""


def test_TC_AIV_ASP_083_old_asset_number_only_when_old_asset_number_differs():
    """旧資産番号コードは旧資産番号に差異がある場合のみ 65 列目に出力する（D-11・C-20）。"""
    with_diff = _columns_of(_row(comparisons=_comparisons(old=True)))
    without_diff = _columns_of(_row(comparisons=_comparisons(summary=True)))
    assert with_diff[COLUMN_OLD_ASSET_NUMBER - 1] == "OLD1"
    assert without_diff[COLUMN_OLD_ASSET_NUMBER - 1] == ""


def test_TC_AIV_ASP_084_acquisition_date_column_is_always_blank():
    """6 列目 取得日付は棚卸で変更しないため常に空欄（D-12・C-21）。"""
    columns = _columns_of(_row(comparisons=_comparisons_all_diff()))
    assert columns[5] == ""


def test_TC_AIV_ASP_085_manufacturer_only_row_fills_three_columns():
    """メーカー名のみ差異の行は資産番号・資産枝番・64 列目の 3 列だけ（D-13・C-14）。"""
    columns = _columns_of(_row(comparisons=_comparisons(maker=True)))
    filled = {index + 1 for index, value in enumerate(columns) if value}
    assert filled == {1, 2, COLUMN_MANUFACTURER_CODE}


# --- REQ-F-005 CSV の形式 -------------------------------------------------


def test_TC_AIV_ASP_020_csv_has_no_header_and_bom_crlf():
    """ヘッダー行なし・CRLF・UTF-8 BOM 付き（REQ-F-005）。"""
    content = _import_rows((_row(),)).render_csv()
    assert content.startswith(b"\xef\xbb\xbf")
    text = content.decode("utf-8-sig")
    assert text.endswith("\r\n")
    lines = text.split("\r\n")[:-1]
    assert len(lines) == 1
    assert lines[0].startswith("5262,0001,")


def test_TC_AIV_ASP_021_every_line_has_74_separators():
    """1 行あたりの区切り文字は 74 個（75 列固定。REQ-F-005）。"""
    text = _import_rows((_row(), _row(asset_number="1"))).render_csv().decode("utf-8-sig")
    for line in text.split("\r\n")[:-1]:
        assert line.count(",") == ASP_COLUMN_COUNT - 1


def test_TC_AIV_ASP_022_value_with_comma_is_quoted():
    """カンマを含む値は RFC4180 に従い囲む（REQ-F-005）。"""
    row = _row(summary="A,B", comparisons=_comparisons(summary=True))
    text = _import_rows((row,)).render_csv().decode("utf-8-sig")
    assert '"A,B"' in text


def test_TC_AIV_ASP_023_empty_rows_render_empty_bytes():
    """出力対象が 0 件なら空のバイト列（呼び出し側でメッセージ表示に切り替える。REQ-F-008）。"""
    assert _import_rows(()).render_csv() == b""


# --- REQ-F-007 チェック仕様違反の警告 -------------------------------------


def test_TC_AIV_ASP_030_no_warning_for_valid_rows():
    assert _import_rows((_row(),)).warnings().message() == ""


def test_TC_AIV_ASP_031_warning_for_too_long_summary():
    """摘要が 64 byte を超えると警告する（チェック P。REQ-F-007）。"""
    row = _row(summary="あ" * 40, comparisons=_comparisons(summary=True))
    warning = _import_rows((row,)).warnings().message()
    assert warning
    assert "5262" in warning


def test_TC_AIV_ASP_032_full_width_model_number_is_converted_without_warning():
    """型番の全角が半角へ変換されて出力され、警告にならないこと（REQ-F-006・D-15）。"""
    row = _row(serial_number="ＳＮ１００", comparisons=_comparisons(serial=True))
    rows = _import_rows((row,))
    assert rows.rows[0].columns[COLUMN_MODEL_NUMBER - 1] == "SN100"
    assert rows.warnings().message() == ""


def test_TC_AIV_ASP_033_warning_for_non_numeric_branch_number():
    """資産枝番が数字以外なら警告する（チェック I。REQ-F-007）。"""
    row = _row(branch_number="A1")
    assert _import_rows((row,)).warnings().message()


def test_TC_AIV_ASP_034_warning_for_missing_asset_number():
    """資産番号が空なら警告する（チェック O。REQ-F-007）。"""
    row = _row(asset_number="  ")
    assert _import_rows((row,)).warnings().message()


def test_TC_AIV_ASP_035_warning_reports_count():
    """警告には件数を含める（REQ-F-007）。"""
    rows = (_row(asset_number="1", branch_number="A"), _row(asset_number="2", branch_number="B"))
    warning = _import_rows(rows).warnings().message()
    assert "2" in warning


def test_TC_AIV_ASP_036_empty_message_is_defined():
    """0 件時のメッセージ（REQ-F-008）。"""
    assert EMPTY_MESSAGE == "取り込み対象の変更がありません。"


# --- REQ-F-006 整形結果（NormalizedValue・DD-03） ---

VALUE_SUMMARY_CRLF = "前\r\n後"
VALUE_SUMMARY_LF = "前\n後"
VALUE_SUMMARY_CR = "前\r後"
VALUE_SUMMARY_CRLF2 = "A\r\n\r\nB"
VALUE_BRANCH_1 = "1"
VALUE_BRANCH_EMPTY = ""
VALUE_BRANCH_ALPHA = "A1"
VALUE_BRANCH_5DIGIT = "12345"


def test_TC_AIV_ASP_050_summary_crlf_is_replaced_with_space():
    """摘要の CRLF は半角空白 1 つに置換され、置換したことが分かること（REQ-F-006・D-08）。"""
    normalized = NormalizedValue.summary(VALUE_SUMMARY_CRLF)
    assert normalized.value == "前 後"
    assert normalized.newline_replaced is True


def test_TC_AIV_ASP_051_summary_lf_is_replaced_with_space():
    """摘要の LF は半角空白 1 つに置換されること（REQ-F-006）。"""
    normalized = NormalizedValue.summary(VALUE_SUMMARY_LF)
    assert normalized.value == "前 後"
    assert normalized.newline_replaced is True


def test_TC_AIV_ASP_052_summary_cr_is_replaced_with_space():
    """摘要の CR は半角空白 1 つに置換されること（REQ-F-006）。"""
    normalized = NormalizedValue.summary(VALUE_SUMMARY_CR)
    assert normalized.value == "前 後"
    assert normalized.newline_replaced is True


def test_TC_AIV_ASP_053_summary_without_newline_is_not_marked_replaced():
    """改行を含まない摘要は置換したことにならないこと（REQ-F-006）。"""
    normalized = NormalizedValue.summary("前後")
    assert normalized.value == "前後"
    assert normalized.newline_replaced is False


def test_TC_AIV_ASP_054_consecutive_crlf_becomes_two_spaces():
    """連続する CRLF は空白 2 つになり、1 つの CRLF が空白 2 つにならないこと（REQ-F-006）。"""
    assert NormalizedValue.summary(VALUE_SUMMARY_CRLF2).value == "A  B"
    assert NormalizedValue.summary("A\r\nB").value == "A B"


def test_TC_AIV_ASP_055_branch_number_is_zero_padded_when_digits_only():
    """資産枝番は数字のみのとき 4 桁ゼロ埋めになること（REQ-F-006）。"""
    assert NormalizedValue.branch_number(VALUE_BRANCH_1).value == "0001"
    assert NormalizedValue.branch_number("12").value == "0012"
    assert NormalizedValue.branch_number("1234").value == "1234"


def test_TC_AIV_ASP_056_empty_branch_number_stays_empty():
    """資産枝番が空ならゼロ埋めせず空欄のままになること（REQ-F-006）。"""
    assert NormalizedValue.branch_number(VALUE_BRANCH_EMPTY).value == ""


def test_TC_AIV_ASP_057_non_numeric_branch_number_is_kept_as_is():
    """資産枝番が数字以外を含むならゼロ埋めせずそのまま返ること（REQ-F-006）。"""
    assert NormalizedValue.branch_number(VALUE_BRANCH_ALPHA).value == "A1"


def test_TC_AIV_ASP_058_five_digit_branch_number_is_not_truncated():
    """資産枝番が 5 桁の数字でも切り詰めずそのまま返ること（REQ-F-006）。"""
    assert NormalizedValue.branch_number(VALUE_BRANCH_5DIGIT).value == "12345"


def test_TC_AIV_ASP_059_plain_values_are_trimmed_only():
    """資産番号・管理部門コード・シリアルNo. は前後の空白を除くだけであること（REQ-F-006）。"""
    normalized = NormalizedValue.trimmed("  5262  ")
    assert normalized.value == "5262"
    assert normalized.newline_replaced is False


# --- REQ-F-007 チェック仕様（AspFieldCheck） ---

VALUE_DEPT_12 = "A" * 12
VALUE_DEPT_13 = "A" * 13
VALUE_MODEL_24 = "A" * 24
VALUE_MODEL_25 = "A" * 25
VALUE_ASSET_13 = "A" * 13
VALUE_SUMMARY_64 = "あ" * 32
VALUE_SUMMARY_65 = "あ" * 32 + "A"
VALUE_SUMMARY_CP932_NG = "𠮟"
VALUE_BRANCH_FULLWIDTH = "ＡＢＣＤＥ"
VALUE_MODEL_FULLWIDTH = "ＡＢＣ－１２３"


def test_TC_AIV_ASP_037_empty_branch_number_violates_required_check():
    """資産枝番が空だと必須入力（チェック O）違反になること（REQ-F-006・REQ-F-007）。"""
    violations = ASP_FIELD_CHECKS[COLUMN_BRANCH_NUMBER].violations(VALUE_BRANCH_EMPTY)
    assert len(violations) == 1


def test_TC_AIV_ASP_038_summary_at_max_bytes_has_no_violation():
    """摘要が領域長ちょうど（64 byte）なら違反にならないこと（REQ-F-007）。"""
    assert ASP_FIELD_CHECKS[COLUMN_SUMMARY].violations(VALUE_SUMMARY_64) == ()


def test_TC_AIV_ASP_039_department_code_boundary_of_max_bytes():
    """管理部門コードは 12 byte まで許容し、13 byte で違反になること（REQ-F-007）。"""
    check = ASP_FIELD_CHECKS[COLUMN_DEPARTMENT_CODE]
    assert check.violations(VALUE_DEPT_12) == ()
    assert len(check.violations(VALUE_DEPT_13)) == 1


def test_TC_AIV_ASP_040_model_number_boundary_of_max_bytes():
    """型番は 24 byte まで許容し、25 byte で違反になること（REQ-F-007）。"""
    check = ASP_FIELD_CHECKS[COLUMN_MODEL_NUMBER]
    assert check.violations(VALUE_MODEL_24) == ()
    assert len(check.violations(VALUE_MODEL_25)) == 1


def test_TC_AIV_ASP_041_asset_number_over_max_bytes_is_violation():
    """資産番号が 12 byte を超えると違反になること（REQ-F-007）。"""
    assert ASP_FIELD_CHECKS[COLUMN_ASSET_NUMBER].violations(VALUE_ASSET_13)


def test_TC_AIV_ASP_042_value_not_encodable_in_cp932_is_evaluated_without_error():
    """cp932 で表現できない文字を含んでも例外を送出せず評価されること（REQ-F-007）。"""
    assert ASP_FIELD_CHECKS[COLUMN_SUMMARY].violations(VALUE_SUMMARY_CP932_NG) == ()


def test_TC_AIV_ASP_046_violation_reason_carries_label_and_column_position():
    """違反理由に項目名と ASP 上の列位置が含まれること（REQ-F-007）。"""
    violations = ASP_FIELD_CHECKS[COLUMN_MODEL_NUMBER].violations(VALUE_MODEL_FULLWIDTH)
    assert violations[0].startswith("型番（16 列目）")


def test_TC_AIV_ASP_047_field_check_position_matches_its_dictionary_key():
    """`ASP_FIELD_CHECKS` のキーと `AspFieldCheck.position` が一致すること（REQ-F-007）。"""
    assert all(column == check.position for column, check in ASP_FIELD_CHECKS.items())


def test_TC_AIV_ASP_043_multiple_violations_are_all_reported():
    """1 つの値に複数の違反があるとき、すべての違反理由が返ること（REQ-F-007）。"""
    violations = ASP_FIELD_CHECKS[COLUMN_BRANCH_NUMBER].violations(VALUE_BRANCH_FULLWIDTH)
    assert len(violations) >= 2


ADDED_CODE_COLUMNS = (
    COLUMN_MANAGER_CODE,
    COLUMN_USAGE_CATEGORY_CODE,
    COLUMN_MANUFACTURER_CODE,
    COLUMN_OLD_ASSET_NUMBER,
)
VALUE_CODE_12 = "A" * 12
VALUE_CODE_13 = "A" * 13
VALUE_CODE_FULLWIDTH = "ＡＢＣ"


def test_TC_AIV_ASP_044_added_code_columns_boundary_of_max_bytes():
    """追加 4 列は 12 byte まで許容し、13 byte で違反になること（REQ-F-007）。"""
    for column in ADDED_CODE_COLUMNS:
        check = ASP_FIELD_CHECKS[column]
        assert check.violations(VALUE_CODE_12) == ()
        assert len(check.violations(VALUE_CODE_13)) == 1


def test_TC_AIV_ASP_045_added_code_columns_reject_full_width():
    """追加 4 列に全角が混入すると違反になること（チェック M。REQ-F-007）。"""
    for column in ADDED_CODE_COLUMNS:
        assert len(ASP_FIELD_CHECKS[column].violations(VALUE_CODE_FULLWIDTH)) == 1


# --- REQ-F-003 管理部門コード（DepartmentCode） ---

VALUE_SITE_CODE_PADDED = " 001 "


def test_TC_AIV_ASP_070_department_code_is_trimmed_from_site_code():
    """管理部門コードは棚卸データの拠点コードから前後の空白を除いて生成されること（REQ-F-003・REQ-F-006）。"""
    assert DepartmentCode.from_site_code(VALUE_SITE_CODE_PADDED).value == "001"


def test_TC_AIV_ASP_071_department_code_over_max_bytes_is_reported():
    """管理部門コードが 12 byte を超えると違反として報告されること（REQ-F-007）。"""
    assert len(DepartmentCode.from_site_code(VALUE_DEPT_13).violations()) == 1


def test_TC_AIV_ASP_072_empty_department_code_is_allowed():
    """管理部門コードが空でも例外にならず、違反にもならないこと（REQ-F-003）。"""
    department_code = DepartmentCode.from_site_code("")
    assert department_code.value == ""
    assert department_code.violations() == ()


# --- REQ-F-007 警告（AspImportWarning / AspImportWarnings・DD-04） ---

LABEL_FIRST = "5262-0001"
LABEL_SECOND = "5263-0001"
DETAIL_BRANCH_EMPTY = "資産枝番（2 列目）が空です"
DETAIL_SUMMARY_LENGTH = "摘要（38 列目）が 64 byte を超えています"
DETAIL_MODEL_FULLWIDTH = "型番（16 列目）に半角英数記号以外が含まれます"


def _check_violation(
    asset_label: str,
    detail: str = DETAIL_BRANCH_EMPTY,
    *,
    position: int = COLUMN_BRANCH_NUMBER,
    value: str = "",
) -> AspImportWarning:
    """チェック仕様違反の警告を 1 件つくる。"""
    return AspImportWarning(
        kind=AspWarningKind.CHECK_VIOLATION,
        asset_label=asset_label,
        detail=detail,
        position=position,
        value=value,
    )


def _newline_replaced(asset_label: str) -> AspImportWarning:
    """摘要の改行置換の警告を 1 件つくる。"""
    return AspImportWarning(
        kind=AspWarningKind.NEWLINE_REPLACED, asset_label=asset_label, detail="摘要の改行を置換しました"
    )


def test_TC_AIV_ASP_060_of_kind_returns_only_the_given_kind():
    """`of_kind()` は指定した種別の警告だけを返すこと（REQ-F-007）。"""
    warnings = AspImportWarnings(
        (
            _check_violation(LABEL_FIRST),
            _check_violation(LABEL_SECOND),
            _newline_replaced(LABEL_FIRST),
        )
    )
    assert len(warnings.of_kind(AspWarningKind.NEWLINE_REPLACED)) == 1
    assert len(warnings.of_kind(AspWarningKind.CHECK_VIOLATION)) == 2


def test_TC_AIV_ASP_061_asset_labels_are_deduplicated():
    """`asset_labels()` は同じ資産の重複を除いて返すこと（REQ-F-007）。"""
    warnings = AspImportWarnings(
        (
            _check_violation(LABEL_FIRST, DETAIL_BRANCH_EMPTY),
            _check_violation(LABEL_FIRST, DETAIL_SUMMARY_LENGTH),
        )
    )
    assert warnings.asset_labels() == (LABEL_FIRST,)


def test_TC_AIV_ASP_062_listed_assets_are_capped_at_ten():
    """資産番号の列挙は 10 件を上限とし、超過分が「ほか N 件」に丸められること（REQ-F-007）。"""
    warnings = AspImportWarnings(
        tuple(_check_violation(f"526{index:02d}-0001") for index in range(12))
    )
    message = warnings.message()
    assert "52600-0001" in message
    assert "52609-0001" in message
    assert "52610-0001" not in message
    assert "ほか 2 件" in message


def test_TC_AIV_ASP_063_two_kinds_are_joined_with_a_newline():
    """チェック仕様違反と改行置換の両方があるとき 2 種別が改行で連結されること（REQ-F-007・C-15）。"""
    warnings = AspImportWarnings((_check_violation(LABEL_FIRST), _newline_replaced(LABEL_SECOND)))
    lines = warnings.message().split("\n")
    assert len(lines) == 3  # 見出し + 明細 1 行 + 改行置換の文
    assert "ASP のチェック仕様に反する値が 1 件あります" in lines[0]
    assert lines[1] == f"・{DETAIL_BRANCH_EMPTY} — {LABEL_FIRST}"
    assert "摘要の改行を半角空白に置き換えた行が 1 件あります" in lines[2]


def test_TC_AIV_ASP_067_detail_lines_are_grouped_by_reason():
    """警告文の明細行が違反理由ごとにまとめられること（REQ-F-007）。"""
    warnings = AspImportWarnings(
        (
            _check_violation(LABEL_FIRST, DETAIL_MODEL_FULLWIDTH, position=COLUMN_MODEL_NUMBER),
            _check_violation(LABEL_SECOND, DETAIL_MODEL_FULLWIDTH, position=COLUMN_MODEL_NUMBER),
            _check_violation("5264-0001", DETAIL_SUMMARY_LENGTH, position=COLUMN_SUMMARY),
        )
    )
    details = [line for line in warnings.message().split("\n") if line.startswith("・")]
    assert len(details) == 2
    assert details[0] == f"・{DETAIL_MODEL_FULLWIDTH} — {LABEL_FIRST}、{LABEL_SECOND}"


def test_TC_AIV_ASP_068_detail_line_shows_the_offending_value():
    """明細行に該当値が「」付きで示されること（REQ-F-007）。"""
    warnings = AspImportWarnings(
        (
            _check_violation(
                LABEL_FIRST,
                DETAIL_MODEL_FULLWIDTH,
                position=COLUMN_MODEL_NUMBER,
                value=VALUE_MODEL_FULLWIDTH,
            ),
        )
    )
    assert f"{LABEL_FIRST}「{VALUE_MODEL_FULLWIDTH}」" in warnings.message()


def test_TC_AIV_ASP_069_long_value_is_abbreviated_at_twenty_characters():
    """20 文字を超える値は先頭 20 文字＋`…` に丸められること（REQ-F-007）。"""
    value = "あ" * 40
    warnings = AspImportWarnings(
        (
            _check_violation(
                LABEL_FIRST, DETAIL_SUMMARY_LENGTH, position=COLUMN_SUMMARY, value=value
            ),
        )
    )
    message = warnings.message()
    assert f"「{"あ" * 20}…」" in message
    assert "あ" * 21 not in message


def test_TC_AIV_ASP_073_empty_value_is_shown_without_quotation_marks():
    """値が空の違反（チェック O）では「」を付けないこと（REQ-F-007）。"""
    warnings = AspImportWarnings((_check_violation(LABEL_FIRST, value=""),))
    message = warnings.message()
    assert "「" not in message
    assert message.endswith(LABEL_FIRST)


def test_TC_AIV_ASP_074_detail_lines_are_sorted_by_column_position():
    """明細行が ASP 上の列位置の昇順に並ぶこと（REQ-F-007）。"""
    warnings = AspImportWarnings(
        (
            _check_violation(LABEL_FIRST, DETAIL_SUMMARY_LENGTH, position=COLUMN_SUMMARY),
            _check_violation(LABEL_SECOND, DETAIL_MODEL_FULLWIDTH, position=COLUMN_MODEL_NUMBER),
        )
    )
    details = [line for line in warnings.message().split("\n") if line.startswith("・")]
    assert details[0].startswith(f"・{DETAIL_MODEL_FULLWIDTH}")
    assert details[1].startswith(f"・{DETAIL_SUMMARY_LENGTH}")


def test_TC_AIV_ASP_075_one_asset_with_two_reasons_is_counted_once():
    """1 つの資産が複数の理由に該当しても見出しの件数は 1 件になること（REQ-F-007）。"""
    warnings = AspImportWarnings(
        (
            _check_violation(LABEL_FIRST, DETAIL_MODEL_FULLWIDTH, position=COLUMN_MODEL_NUMBER),
            _check_violation(LABEL_FIRST, DETAIL_SUMMARY_LENGTH, position=COLUMN_SUMMARY),
        )
    )
    lines = warnings.message().split("\n")
    assert "反する値が 1 件あります" in lines[0]
    assert len([line for line in lines if line.startswith("・")]) == 2


def test_TC_AIV_ASP_064_message_is_empty_when_there_is_no_warning():
    """警告が無いとき警告文は空文字になること（REQ-F-007）。"""
    assert AspImportWarnings(()).message() == ""


def test_TC_AIV_ASP_065_site_unavailable_warning_is_added_only_once():
    """拠点マスタ縮退の警告は出力全体に 1 件だけ付与されること（REQ-F-009・DD-02）。"""
    row_warnings = AspImportWarnings(
        tuple(_check_violation(f"526{index}-0001") for index in range(5))
    )
    warnings = row_warnings.with_site_unavailable()
    assert len(warnings.of_kind(AspWarningKind.SITE_UNAVAILABLE)) == 1
    assert "管理部門コードは出力していません" in warnings.message()


def test_TC_AIV_ASP_066_unavailable_message_is_defined_as_a_constant():
    """突合結果が無いときのメッセージが定数として定義されていること（REQ-F-009・C-16）。"""
    assert UNAVAILABLE_MESSAGE == "棚卸を選び直してください。"


# --- REQ-F-003 貼り付けレイアウトと 1 行（AspPasteLayout / AspImportRow） ---


def test_TC_AIV_ASP_010b_blank_columns_are_75_empty_strings():
    """`blank_columns()` は 75 個の空文字を返すこと（REQ-F-003・C-03）。"""
    blanks = AspPasteLayout.blank_columns()
    assert len(blanks) == ASP_COLUMN_COUNT
    assert set(blanks) == {""}


def test_TC_AIV_ASP_019_asset_label_joins_asset_number_and_branch_number():
    """`asset_label` は資産番号と資産枝番を連結した識別ラベルになること（REQ-F-007）。"""
    import_row = AspImportRow.from_reconcile_row(_row(asset_number="5262", branch_number="1"))
    assert import_row.asset_label == "5262-0001"


def test_TC_AIV_ASP_019b_asset_label_is_asset_number_only_when_branch_is_empty():
    """資産枝番が空のとき `asset_label` は資産番号のみになること（REQ-F-007）。"""
    import_row = AspImportRow.from_reconcile_row(_row(asset_number="5262", branch_number=""))
    assert import_row.asset_label == "5262"


# --- REQ-F-005 取り込み用データ（AspImportRows） ---

VALUE_SUMMARY_WITH_QUOTE = 'A"B'


def _import_rows(rows, *, site_warning: bool = False) -> AspImportRows:
    """突合結果の行から取り込み用データを組み立てる。"""
    return AspImportRows.from_rows(
        tuple(AspImportRow.from_reconcile_row(row) for row in rows), site_warning=site_warning
    )


def test_TC_AIV_ASP_024_double_quote_in_value_is_escaped_and_quoted():
    """ダブルクォートを含む値は `""` にエスケープして囲まれること（REQ-F-005）。"""
    import_rows = _import_rows(
        [_row(summary=VALUE_SUMMARY_WITH_QUOTE, comparisons=_comparisons(summary=True))]
    )
    assert '"A""B"' in import_rows.render_csv().decode("utf-8-sig")


def test_TC_AIV_ASP_025_warnings_are_collected_from_every_row():
    """`warnings()` が全行の警告を連結して返すこと（REQ-F-007・C-10）。"""
    import_rows = _import_rows(
        [
            _row(asset_number="5262", branch_number=""),
            _row(asset_number="5263", branch_number=""),
            _row(asset_number="5264", branch_number="1"),
        ]
    )
    violations = import_rows.warnings().of_kind(AspWarningKind.CHECK_VIOLATION)
    assert len(violations) == 2
    assert violations.asset_labels() == ("5262", "5263")


def test_TC_AIV_ASP_026_rendering_twice_produces_identical_bytes():
    """同一の入力から繰り返し描画しても内容が変わらないこと（REQ-NF-005・C-17）。"""
    import_rows = _import_rows(
        [
            _row(asset_number="5262", summary="摘要1", comparisons=_comparisons(summary=True)),
            _row(asset_number="5263", site_code="002", comparisons=_comparisons(site=True)),
            _row(asset_number="5264", serial_number="SN-1", comparisons=_comparisons(serial=True)),
        ]
    )
    assert import_rows.render_csv() == import_rows.render_csv()


def test_TC_AIV_ASP_027_department_code_is_blank_when_site_master_is_unavailable():
    """拠点マスタ縮退時は管理部門コードを空欄にし、警告を 1 件だけ付けること（REQ-F-009・DD-02）。"""
    import_rows = _import_rows(
        [_row(site_code="002", comparisons=_comparisons(site=True))], site_warning=True
    )
    columns = import_rows.rows[0].columns
    assert columns[COLUMN_DEPARTMENT_CODE - 1] == ""
    assert len(import_rows.warnings().of_kind(AspWarningKind.SITE_UNAVAILABLE)) == 1


# --- REQ-F-002 修正対象行のコレクション（AmendmentRows） ---

ROWS_1000 = tuple(_row(asset_number=f"{5000 + index}") for index in range(1000))


def test_TC_AIV_ASP_004_unmatched_rows_are_not_amendment_rows():
    """未棚卸・台帳外の行は修正対象行に含まれないこと（REQ-F-002・C-02）。"""
    rows = (
        _row(status=MatchStatus.ASSET_ONLY, tone=RowTone.NONE),
        _row(status=MatchStatus.INVENTORY_ONLY, tone=RowTone.NONE),
    )
    assert AmendmentRows.select_from(rows).count() == 0


def test_TC_AIV_ASP_005_matched_row_without_diff_is_not_an_amendment_row():
    """変化点のない棚卸済み行は修正対象行に含まれないこと（REQ-F-002・C-02）。"""
    rows = (_row(tone=RowTone.MATCH_CLEAN, has_diff=False, comparisons=_comparisons()),)
    assert AmendmentRows.select_from(rows).count() == 0


def test_TC_AIV_ASP_006_no_amendment_row_makes_the_collection_empty():
    """修正対象行が 0 件のとき `is_empty()` が真・`count()` が 0 になること（REQ-F-008・C-07）。"""
    rows = tuple(
        _row(tone=RowTone.MATCH_CLEAN, has_diff=False, comparisons=_comparisons())
        for _ in range(3)
    )
    amendment_rows = AmendmentRows.select_from(rows)
    assert amendment_rows.is_empty() is True
    assert amendment_rows.count() == 0


def test_TC_AIV_ASP_007_single_amendment_row_makes_the_collection_not_empty():
    """修正対象行が 1 件のとき `is_empty()` が偽・`count()` が 1 になること（REQ-F-002）。"""
    amendment_rows = AmendmentRows.select_from((_row(),))
    assert amendment_rows.is_empty() is False
    assert amendment_rows.count() == 1


def test_TC_AIV_ASP_008_all_amendment_rows_are_kept_in_input_order():
    """修正対象行が多数でも全件抽出され、入力順が保たれること（REQ-NF-004・D-10）。"""
    amendment_rows = AmendmentRows.select_from(ROWS_1000)
    assert amendment_rows.count() == 1000
    assert tuple(row.asset_number for row in amendment_rows.rows) == tuple(
        row.asset_number for row in ROWS_1000
    )


def test_TC_AIV_ASP_009_to_import_rows_returns_the_same_number_of_rows():
    """`to_import_rows()` は修正対象行と同数の取り込み用データを返すこと（REQ-F-003）。"""
    rows = tuple(_row(asset_number=f"526{index}") for index in range(3))
    assert len(AmendmentRows.select_from(rows).to_import_rows().rows) == 3


# --- REQ-F-006 値を ASP の書式へ寄せる（AdjustedValue・D-14・DD-10） ---

VALUE_MANAGER_PROLONGED = "DDGー380C"  # 4 文字目が U+30FC（全角長音記号）
VALUE_MANAGER_DASHES = ("AB\u2010" + "1", "AB\u2011" + "1", "AB\u2012" + "1", "AB\u2013" + "1",
                        "AB\u2014" + "1", "AB\u2015" + "1", "AB\u2212" + "1")
VALUE_MANAGER_KANA = "モーター100"
VALUE_MANAGER_PROLONGED_ONLY = "ーAB123"
VALUE_MANAGER_16 = "RGSHL4-60-50-L-S"
VALUE_MANAGER_12 = "A" * 12
VALUE_SUMMARY_66 = "あ" * 32 + "い"


def _adjusted(column: int, value: str):
    return ASP_FIELD_CHECKS[column].adjusted(value)


def test_TC_AIV_ASP_086_full_width_alphanumeric_is_converted_to_half_width():
    """全角英数字・全角ハイフンが半角へ変換されること（REQ-F-006・C-23）。"""
    adjusted = _adjusted(COLUMN_MANAGER_CODE, "ＡＢＣ－１２３")
    assert adjusted.value == "ABC-123"
    assert adjusted.half_width_converted is True
    assert ASP_FIELD_CHECKS[COLUMN_MANAGER_CODE].violations(adjusted.value) == ()


def test_TC_AIV_ASP_087_dashes_not_normalized_by_nfkc_are_converted_to_hyphen():
    """NFKC で変換されないダッシュ類が半角ハイフンへ変換されること（REQ-F-006・C-23）。"""
    for value in VALUE_MANAGER_DASHES:
        adjusted = _adjusted(COLUMN_MANAGER_CODE, value)
        assert adjusted.value == "AB-1", value
        assert ASP_FIELD_CHECKS[COLUMN_MANAGER_CODE].violations(adjusted.value) == ()


def test_TC_AIV_ASP_088_full_width_quotation_marks_are_converted():
    """全角引用符が半角へ変換されること（REQ-F-006・C-23）。"""
    assert _adjusted(COLUMN_MANAGER_CODE, "A\u2019B").value == "A'B"
    assert _adjusted(COLUMN_MANAGER_CODE, "A\u201cB\u201d").value == 'A"B"'


def test_TC_AIV_ASP_089_prolonged_sound_mark_is_converted_to_hyphen():
    """全角長音記号が半角ハイフンへ変換されること（実データ 5 件。REQ-F-006・C-23）。"""
    for value, expected in (
        (VALUE_MANAGER_PROLONGED, "DDG-380C"),
        ("ZSー302R", "ZS-302R"),
        ("GMEーR1500", "GME-R1500"),
    ):
        adjusted = _adjusted(COLUMN_MANAGER_CODE, value)
        assert adjusted.value == expected
        assert ASP_FIELD_CHECKS[COLUMN_MANAGER_CODE].violations(adjusted.value) == ()


def test_TC_AIV_ASP_090_prolonged_sound_mark_in_japanese_word_is_kept():
    """かな・カナ・漢字を含む値の長音記号は変換せず、違反として残ること（REQ-F-006・C-24）。"""
    for value in (VALUE_MANAGER_KANA, "ﾓｰﾀｰ100", "巻ーA"):
        adjusted = _adjusted(COLUMN_MANAGER_CODE, value)
        assert "-" not in adjusted.value, value
        assert len(ASP_FIELD_CHECKS[COLUMN_MANAGER_CODE].violations(adjusted.value)) == 1


def test_TC_AIV_ASP_091_prolonged_sound_mark_without_japanese_is_converted():
    """日本語文字を含まない値の長音記号は変換されること（REQ-F-006・C-24）。"""
    adjusted = _adjusted(COLUMN_MANAGER_CODE, VALUE_MANAGER_PROLONGED_ONLY)
    assert adjusted.value == "-AB123"
    assert ASP_FIELD_CHECKS[COLUMN_MANAGER_CODE].violations(adjusted.value) == ()


def test_TC_AIV_ASP_092_ideographic_space_is_converted_to_half_width_space():
    """全角空白が半角空白へ変換されること（REQ-F-006・C-23）。"""
    adjusted = _adjusted(COLUMN_MANAGER_CODE, "AB\u30001")
    assert adjusted.value == "AB 1"
    assert ASP_FIELD_CHECKS[COLUMN_MANAGER_CODE].violations(adjusted.value) == ()


def test_TC_AIV_ASP_093_half_width_value_is_not_marked_as_converted():
    """半角のみの値は変換されたことにならないこと（REQ-F-006）。"""
    adjusted = _adjusted(COLUMN_MANAGER_CODE, "ABC-123")
    assert adjusted.value == "ABC-123"
    assert adjusted.half_width_converted is False
    assert adjusted.truncated is False


def test_TC_AIV_ASP_094_summary_is_not_converted_to_half_width():
    """摘要（チェック P）は半角変換されないこと（REQ-F-006・C-23）。"""
    adjusted = _adjusted(COLUMN_SUMMARY, "全角の摘要ＡＢＣ")
    assert adjusted.value == "全角の摘要ＡＢＣ"
    assert adjusted.half_width_converted is False


def test_TC_AIV_ASP_095_value_over_max_bytes_is_truncated():
    """領域長を超える値は末尾が切り捨てられること（実データ 1 件。REQ-F-006・C-25）。"""
    adjusted = _adjusted(COLUMN_MANAGER_CODE, VALUE_MANAGER_16)
    assert adjusted.value == "RGSHL4-60-50"
    assert adjusted.truncated is True
    assert ASP_FIELD_CHECKS[COLUMN_MANAGER_CODE].violations(adjusted.value) == ()


def test_TC_AIV_ASP_096_truncation_does_not_split_a_full_width_character():
    """切り捨てで全角 1 文字が分断されないこと（REQ-F-006・C-25）。"""
    adjusted = _adjusted(COLUMN_SUMMARY, VALUE_SUMMARY_66)
    assert adjusted.truncated is True
    assert adjusted.value == "あ" * 32
    assert len(adjusted.value.encode("cp932")) == 64


def test_TC_AIV_ASP_097_value_at_max_bytes_is_not_truncated():
    """領域長ちょうどの値は切り捨てられないこと（REQ-F-006）。"""
    adjusted = _adjusted(COLUMN_MANAGER_CODE, VALUE_MANAGER_12)
    assert adjusted.value == VALUE_MANAGER_12
    assert adjusted.truncated is False


def test_TC_AIV_ASP_098_key_columns_are_never_truncated():
    """資産番号・資産枝番は領域長を超えても切り捨てず違反として残すこと（REQ-F-006・C-25）。"""
    asset_number = _adjusted(COLUMN_ASSET_NUMBER, VALUE_ASSET_13)
    assert asset_number.value == VALUE_ASSET_13
    assert asset_number.truncated is False
    assert len(ASP_FIELD_CHECKS[COLUMN_ASSET_NUMBER].violations(asset_number.value)) == 1

    branch_number = _adjusted(COLUMN_BRANCH_NUMBER, "12345")
    assert branch_number.value == "12345"
    assert branch_number.truncated is False
    assert len(ASP_FIELD_CHECKS[COLUMN_BRANCH_NUMBER].violations(branch_number.value)) == 1


def test_TC_AIV_ASP_099_half_width_conversion_is_applied_before_truncation():
    """半角変換のあとに切り捨てが適用されること（REQ-F-006・C-23・C-25）。"""
    adjusted = _adjusted(COLUMN_MANAGER_CODE, "Ａ" * 13)
    assert adjusted.half_width_converted is True
    assert adjusted.truncated is True
    assert adjusted.value == "A" * 12


def test_TC_AIV_ASP_100_empty_value_is_neither_converted_nor_truncated():
    """空文字は変換も切り捨てもされないこと（REQ-F-006）。"""
    adjusted = _adjusted(COLUMN_MANAGER_CODE, "")
    assert adjusted.value == ""
    assert adjusted.half_width_converted is False
    assert adjusted.truncated is False


# --- REQ-F-007 寄せた事実の警告（D-14） ---


def _warnings_of(**kwargs) -> AspImportWarnings:
    return AspImportRow.from_reconcile_row(
        _row(comparisons=_comparisons_all_diff(), **kwargs)
    ).warnings


def test_TC_AIV_ASP_101_converted_row_reports_no_warning():
    """半角変換しただけの行が警告にならないこと（REQ-F-007・C-23・D-15）。"""
    warnings = _warnings_of(manager_code=VALUE_MANAGER_PROLONGED)
    assert len(warnings) == 0
    assert warnings.message() == ""


def test_TC_AIV_ASP_102_truncated_row_reports_value_truncated_warning():
    """切り捨てた行が `VALUE_TRUNCATED` の警告になること（REQ-F-007・C-25）。"""
    warnings = _warnings_of(manager_code=VALUE_MANAGER_16)
    assert len(warnings.of_kind(AspWarningKind.VALUE_TRUNCATED)) == 1
    assert len(warnings.of_kind(AspWarningKind.CHECK_VIOLATION)) == 0


def test_TC_AIV_ASP_103_warning_message_shows_value_before_and_after():
    """警告文に寄せる前と寄せたあとの値が並ぶこと（REQ-F-007・C-25）。"""
    message = _warnings_of(manager_code=VALUE_MANAGER_16).message()
    assert f"「{VALUE_MANAGER_16}」→「RGSHL4-60-50」" in message


def test_TC_AIV_ASP_104_warning_blocks_follow_the_defined_order():
    """警告ブロックが 違反 → 切り捨て → 改行置換 → 拠点マスタ縮退 の順に並ぶこと（REQ-F-007・D-14・D-15）。"""
    warnings = AspImportWarnings(
        (
            _check_violation(LABEL_FIRST, DETAIL_BRANCH_EMPTY, position=COLUMN_BRANCH_NUMBER),
            AspImportWarning(
                kind=AspWarningKind.VALUE_TRUNCATED,
                asset_label=LABEL_FIRST,
                detail="管理者コード（44 列目）を 12 byte に切り詰めました",
                position=COLUMN_MANAGER_CODE,
                value=VALUE_MANAGER_16,
                adjusted_value="RGSHL4-60-50",
            ),
            AspImportWarning(
                kind=AspWarningKind.NEWLINE_REPLACED,
                asset_label=LABEL_FIRST,
                detail="摘要の改行を半角空白に置き換えました",
                position=COLUMN_SUMMARY,
            ),
        )
    ).with_site_unavailable()

    lines = warnings.message().split("\n")
    order = [
        next(index for index, line in enumerate(lines) if keyword in line)
        for keyword in ("チェック仕様に反する", "切り詰めた値", "改行を半角空白", "拠点マスタ")
    ]
    assert order == sorted(order)
