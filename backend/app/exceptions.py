"""应用异常定义。

Service 层通过 BusinessError 传递业务违规信息，
Router 层捕获后转为 HTTPException（409 Conflict）。
"""


class BusinessError(Exception):
    """业务逻辑异常。

    Service 层在校验失败时抛出，Router 层捕获后转为 HTTP 409 响应。

    Args:
        message: 异常描述，将作为 HTTP 响应的 detail。
    """

    pass
