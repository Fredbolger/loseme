from sentence_transformers import CrossEncoder


class CrossEncoderEmbeddingProvider:
    def __init__(self, model_name: str):
        if not model_name:
            raise ValueError("Model name must be provided for CrossEncoderEmbeddingProvider.")
        self.model = CrossEncoder(model_name)

    def encode(self, texts):
        return self.model.encode(texts)
