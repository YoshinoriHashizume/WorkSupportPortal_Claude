class DesknetApiError(Exception):
    pass


class DesknetAccessKeyMissingError(DesknetApiError):
    pass


def format_desknet_user_error_message(message: str) -> str:
    text = (message or "").strip()
    if "W10008" in text or "アクセス権がありません" in text:
        from django.conf import settings

        if str(getattr(settings, "DESKNETS_ASSET_INVENTORY_LOGIN_ID", "") or "").strip():
            return (
                "desknet's の棚卸データ取得に失敗しました。"
                "サービス連携アカウント（DESKNETS_ASSET_INVENTORY_LOGIN_ID）の参照権限を管理者にご確認ください。"
            )
        return (
            "desknet's の棚卸関連アプリに参照権限がありません。"
            "ポータルの総務権限とは別に、desknet's 側のアプリ参照権限が必要です。"
            "管理者へ desknet's の権限設定、またはポータルのサービス連携アカウント設定を依頼してください。"
        )
    return text
