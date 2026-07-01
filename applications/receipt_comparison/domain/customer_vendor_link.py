from __future__ import annotations


def resolve_purchase_vendor_code(
    customer_code: str,
    *,
    cust_vend_cd: str | None,
    vendor_exists_for_customer_code: bool,
) -> str | None:
    """M_CUST と M_VEND_CTRL の定義に沿って購買取引先コードを決定する。"""
    customer = str(customer_code or "").strip()
    if not customer:
        return None

    linked = str(cust_vend_cd or "").strip()
    if linked:
        return linked
    if vendor_exists_for_customer_code:
        return customer
    return None


def vendor_match_codes(
    customer_code: str,
    purchase_vendor_code: str | None,
    extra_vendor_codes: list[str] | None = None,
) -> list[str]:
    """受領TXT照合・MARI取得に使う取引先コード一覧（重複除去・昇順）。"""
    codes: set[str] = set()
    customer = str(customer_code or "").strip()
    if customer:
        codes.add(customer)
    purchase = str(purchase_vendor_code or "").strip()
    if purchase:
        codes.add(purchase)
    for code in extra_vendor_codes or []:
        normalized = str(code or "").strip()
        if normalized:
            codes.add(normalized)
    return sorted(codes)
