from __future__ import annotations

from application.inventory_order_alert.domain.repositories.ports import (
    LoadAppSettings,
    LookupVendorNames,
    SaveAppSettings,
)
from application.inventory_order_alert.domain.value_objects.app_settings import (
    AppSettings,
    parse_settings_payload,
    settings_payload,
)
from application.inventory_order_alert.domain.value_objects.direct_shipment import (
    DirectShipmentSuppliers,
    VendorName,
)
from application.inventory_order_alert.domain.value_objects.errors import VendorLookupUnavailableError


class AppSettingsUseCase:
    """設定画面（§4.2）・設定 API（§8.10）の取得／更新を担う。"""

    def __init__(
        self,
        load_app_settings: LoadAppSettings,
        save_app_settings: SaveAppSettings,
        *,
        lookup_vendor_names: LookupVendorNames | None = None,
    ) -> None:
        self._load_app_settings = load_app_settings
        self._save_app_settings = save_app_settings
        self._lookup_vendor_names = lookup_vendor_names

    def load(self) -> AppSettings:
        return self._load_app_settings()

    def load_payload(self) -> dict[str, object]:
        return settings_payload(self._load_app_settings())

    def load_view(self) -> dict[str, object]:
        """設定値と直送仕入先（V-240）の仕入先名。基幹に接続できなくても返す（12 design §6.3）。"""
        settings = self._load_app_settings()
        return self._view(settings)

    def vendor_names(self, suppliers: DirectShipmentSuppliers) -> list[VendorName]:
        """登録済みの直送仕入先の名前を解決する。基幹に接続できなければ status=unavailable。"""
        codes = list(suppliers.codes)
        if not codes:
            return []
        if self._lookup_vendor_names is None:
            return [VendorName(code, "", "unavailable") for code in codes]
        try:
            names = self._lookup_vendor_names(codes)
        except VendorLookupUnavailableError:
            return [VendorName(code, "", "unavailable") for code in codes]
        return [
            VendorName(code, names[code], "found") if code in names else VendorName(code, "", "not_found")
            for code in codes
        ]

    def save(self, payload: object, *, updated_by: object | None = None) -> dict[str, object]:
        """検証して保存し、保存後の設定値の JSON 表現を返す。

        直送仕入先は新しく加わったコードだけ仕入先マスタで実在を確かめる（12 design §6.1）。
        見つからなければ ValueError、基幹に接続できなければ VendorLookupUnavailableError で、どちらも保存しない。
        """
        return settings_payload(self._save(payload, updated_by=updated_by))

    def save_view(self, payload: object, *, updated_by: object | None = None) -> dict[str, object]:
        """`save` と同じ。応答に直送仕入先の名前を添える（設定 API の PUT 応答）。"""
        return self._view(self._save(payload, updated_by=updated_by))

    def _view(self, settings: AppSettings) -> dict[str, object]:
        return {
            "settings": settings_payload(settings),
            "directShipmentSuppliers": [
                vendor.to_payload() for vendor in self.vendor_names(settings.direct_shipment_suppliers)
            ],
        }

    def _save(self, payload: object, *, updated_by: object | None) -> AppSettings:
        current = self._load_app_settings()
        input_data = parse_settings_payload(payload, current=current)
        self._require_existing_vendors(input_data.direct_shipment_suppliers.added_since(current.direct_shipment_suppliers))
        return self._save_app_settings(
            warning_days=input_data.warning_days,
            stock_stale_days=input_data.stock_stale_days,
            default_lead_time_days=input_data.default_lead_time_days,
            recent_incoming_days=input_data.recent_incoming_days,
            judgement_horizon_days=input_data.judgement_horizon_days,
            stale_order_days=input_data.stale_order_days,
            direct_shipment_suppliers=input_data.direct_shipment_suppliers,
            updated_by=updated_by,
        )

    def _require_existing_vendors(self, new_codes: tuple[str, ...]) -> None:
        if not new_codes or self._lookup_vendor_names is None:
            return
        names = self._lookup_vendor_names(list(new_codes))  # 接続できなければ例外のまま上げる
        missing = [code for code in new_codes if code not in names]
        if missing:
            raise ValueError(f"仕入先マスタに存在しない仕入先コードです: {', '.join(missing)}")
