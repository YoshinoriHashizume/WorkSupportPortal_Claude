from __future__ import annotations

from application.shipment_trend.models import ShipmentTrendBaselineYear


def load_baseline_overrides() -> dict[tuple[str, str], int]:
    """全ユーザー共通の比較基準年オーバーライドを (cust_code, item_cd) → 年 で返す。"""
    return {
        (str(row.cust_code).strip(), str(row.item_cd).strip()): int(row.baseline_fiscal_year)
        for row in ShipmentTrendBaselineYear.objects.all().only(
            "cust_code",
            "item_cd",
            "baseline_fiscal_year",
        )
    }


def load_baseline_year(*, cust_code: str, item_cd: str) -> int | None:
    row = (
        ShipmentTrendBaselineYear.objects.filter(
            cust_code=cust_code.strip(),
            item_cd=item_cd.strip(),
        )
        .only("baseline_fiscal_year")
        .first()
    )
    if row is None:
        return None
    return int(row.baseline_fiscal_year)


def save_baseline_year(
    *,
    cust_code: str,
    item_cd: str,
    baseline_fiscal_year: int,
    updated_by: object | None,
) -> None:
    ShipmentTrendBaselineYear.objects.update_or_create(
        cust_code=cust_code.strip(),
        item_cd=item_cd.strip(),
        defaults={
            "baseline_fiscal_year": int(baseline_fiscal_year),
            "updated_by": updated_by,
        },
    )


def delete_baseline_year(*, cust_code: str, item_cd: str) -> bool:
    deleted, _ = ShipmentTrendBaselineYear.objects.filter(
        cust_code=cust_code.strip(),
        item_cd=item_cd.strip(),
    ).delete()
    return deleted > 0
