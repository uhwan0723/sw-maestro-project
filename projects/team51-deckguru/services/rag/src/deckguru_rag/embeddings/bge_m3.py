from typing import Any


class BGEM3Embedding:
    """Dense BGE-M3 embedding wrapper.

    BGE-M3 outputs 1024-dimensional dense vectors and supports Korean text.
    The model is loaded lazily so imports stay cheap for scripts that do not
    embed text.
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-m3",
        *,
        use_fp16: bool = False,
        batch_size: int = 12,
        max_length: int = 8192,
    ) -> None:
        self.model_name = model_name
        self.use_fp16 = use_fp16
        self.batch_size = batch_size
        self.max_length = max_length
        self._model: Any | None = None

    def embed(self, text: str) -> list[float]:
        return self.embed_many([text])[0]

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        output = self._load_model().encode(
            texts,
            batch_size=self.batch_size,
            max_length=self.max_length,
            return_dense=True,
            return_sparse=False,
            return_colbert_vecs=False,
        )
        return [vector.tolist() for vector in output["dense_vecs"]]

    def _load_model(self) -> Any:
        if self._model is None:
            try:
                from FlagEmbedding import BGEM3FlagModel
            except ImportError as exc:
                raise RuntimeError(
                    "FlagEmbedding is not installed. Install RAG dependencies with "
                    "`services/rag/.venv/Scripts/python.exe -m pip install -r "
                    "services/rag/requirements.txt`."
                ) from exc
            self._model = BGEM3FlagModel(self.model_name, use_fp16=self.use_fp16)
        return self._model
