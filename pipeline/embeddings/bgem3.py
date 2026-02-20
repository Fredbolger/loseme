from typing import List
from FlagEmbedding import BGEM3FlagModel
import numpy as np
import torch

from src.domain.embeddings import EmbeddingProvider, EmbeddingOutput
from src.sources.base.models import Chunk

from src.core.config import USE_CUDA

import logging
logger = logging.getLogger(__name__)

class BGEM3EmbeddingProvider(EmbeddingProvider):
    def __init__(self, model_name: str = "BAAI/bge-m3"):
        self.model_name = model_name
        self.model = BGEM3FlagModel(model_name, use_fp16=True)
        self._dimension = 1024
        device = "cuda" if USE_CUDA == "true" else "cpu"

    def dimension(self) -> int:
        return self._dimension

    def embed_query(self, text: str) -> EmbeddingOutput:
        with torch.no_grad():
            embedding = self.model.encode(
                [text],
                return_dense=True,
                return_sparse=True,
                return_colbert_vecs=True,
            )
        dense, sparse, colbert = embedding["dense_vecs"], embedding["lexical_weights"], embedding["colbert_vecs"]
        result = EmbeddingOutput(dense=self._to_numpy(dense[0]), sparse=sparse[0], colbert_vec=self._to_numpy(colbert[0]))
        del embedding, dense, colbert
        return result
    
    def embed_document(self, text: str) -> EmbeddingOutput:
        with torch.no_grad(): 
            embedding = self.model.encode(
                [text],
                return_dense=True,
                return_sparse=True,
                return_colbert_vecs=True,
            )
        dense, sparse, colbert = embedding["dense_vecs"], embedding["lexical_weights"], embedding["colbert_vecs"]
        result = EmbeddingOutput(dense=self._to_numpy(dense[0]), sparse=sparse[0], colbert_vec=self._to_numpy(colbert[0]))
        del embedding, dense, colbert
        return result

    def _to_numpy(self, x):
        if isinstance(x, torch.Tensor):
            return x.detach().cpu().numpy()
        return np.array(x)
