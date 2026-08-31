class DesknetApiError(Exception):
    pass


class DesknetAccessKeyMissingError(DesknetApiError):
    pass


class DesknetAccessKeyExpiredError(DesknetApiError):
    """desknet's がアクセスキーを拒否した(HTTP 401 / 403)。

    アプリの参照権限不足(HTTP 200 + W10008)とは別で、認証そのものが通っていない状態。
    アクセスキーはログイン時に取得したものを使うため、再ログインでしか復旧できない。
    """


#: セッションにアクセスキーが無いときに利用者へ出す文言。
MISSING_KEY_ERROR_MESSAGE = "desknet's のアクセスキーがありません。再ログインしてください。"

#: ログイン時に取得したアクセスキーが失効したときに利用者へ出す文言。
SESSION_EXPIRED_MESSAGE = (
    "desknet's とのセッションが切れました。お手数ですが、もう一度ログインしてください。"
)

#: desknet's 側の棚卸関連アプリに参照権限がないときに利用者へ出す文言。
NO_APP_PERMISSION_MESSAGE = (
    "desknet's の棚卸関連アプリにアクセス権がありません。"
    "閲覧が必要な場合は、システムグループへ desknet's のアクセス権付与をご依頼ください。"
)


def format_desknet_user_error_message(message: str) -> str:
    """desknet's が返したエラーメッセージを利用者向けの文言に直す。

    参照権限がない場合(W10008)は、desknet's の生メッセージではなく
    誰に何を依頼すればよいかが分かる文言に差し替える。
    """
    text = (message or "").strip()
    if "W10008" in text or "アクセス権がありません" in text:
        return NO_APP_PERMISSION_MESSAGE
    return text
