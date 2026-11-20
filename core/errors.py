"""统一业务异常。

服务层只抛 BusinessError，页面 / API 层负责把它转换成用户可读提示。
"""


class BusinessError(Exception):
    """可预期的业务错误。

    code:    稳定的错误码，供页面判断或日志检索
    message: 面向用户的中文提示，不包含堆栈与内部路径
    """

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
