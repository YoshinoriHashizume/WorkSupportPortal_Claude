from __future__ import annotations


def resolve_internal_item_cd(
    *,
    cust_item_cd: str,
    internal_from_ship: str = "",
    internal_from_m_cust_item_pair: str = "",
    internal_from_m_cust_item: str = "",
) -> str:
    """Resolve BOM/incoming key (internal ITEM_CD) from shipment and M_CUST_ITEM hints."""
    if internal_from_ship:
        return internal_from_ship
    if internal_from_m_cust_item_pair:
        return internal_from_m_cust_item_pair
    if internal_from_m_cust_item:
        return internal_from_m_cust_item
    return cust_item_cd


def resolve_cust_code(*, cust_from_ship: str = "") -> str:
    """Return T_SHIP.CUST_CD for shipped rows. Unshipped rows use empty string."""
    return cust_from_ship
