from __future__ import annotations

ADMIN_GROUP_NAME = "管理者"
GENERAL_USER_GROUP_NAME = "一般ユーザー"
MANAGEMENT_GROUP_KEY = "management"
ROLE_GROUP_NAMES = (GENERAL_USER_GROUP_NAME, ADMIN_GROUP_NAME)
DEFAULT_DEPARTMENT_GROUP_NAME = "全社"
MANAGEMENT_MENU_GROUP_KEY = "management"

RECEIPT_COMPARISON_PATH = "/app/production/receipt-comparison"

RECEIPT_COMPARISON_MENU_KEYS = {
    "finished-product": "receipt-comparison-finished-product",
    "supplied-parts": "receipt-comparison-supplied-parts",
    "finished_product": "receipt-comparison-finished-product",
    "supplied_parts": "receipt-comparison-supplied-parts",
}

SENSITIVE_COLUMN_NAMES = {"password", "session_key", "session_data"}
VALID_SORT_DIRECTIONS = {"asc", "desc"}
