class CoinnestError(RuntimeError):
    def __init__(self, status: str):
        super().__init__(status)
