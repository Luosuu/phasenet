import torch.nn as nn

from .transformer import TransformerBlock
from .embedding import BERTEmbedding
import torch

class BERT(nn.Module):
    """
    BERT model : Bidirectional Encoder Representations from Transformers.
    """

    def __init__(self, hidden=768, n_layers=12, attn_heads=12, dropout=0.1):
        """
        :param vocab_size: vocab_size of total words
        :param hidden: BERT model hidden size
        :param n_layers: numbers of Transformer blocks(layers)
        :param attn_heads: number of attention heads
        :param dropout: dropout rate
        """

        super().__init__()
        self.hidden = hidden
        self.n_layers = n_layers
        self.attn_heads = attn_heads

        # paper noted they used 4*hidden_size for ff_network_hidden_size
        self.feed_forward_hidden = hidden * 4

        # embedding for BERT, sum of positional, segment, token embeddings
        # self.embedding = BERTEmbedding(vocab_size=vocab_size, embed_size=hidden)

        # multi-layers transformer blocks, deep network
        self.transformer_blocks = nn.ModuleList(
            [TransformerBlock(hidden, attn_heads, hidden * 4, dropout) for _ in range(n_layers)])
        self.linear_mapping = nn.Linear(hidden * 2, 3000)
        # self.relu = nn.ReLU()

    def forward(self, x):
        # attention masking for padded token
        # torch.ByteTensor([batch_size, 1, seq_len, seq_len)
        # mask = (x > 0).unsqueeze(1).repeat(1, x.size(1), 1).unsqueeze(1)
        mask = None
        # embedding the indexed sequence to sequence of vectors
        # x = self.embedding(x, segment_info)

        # running over multiple transformer blocks
        # x = x.unsqueeze(1)
        for transformer in self.transformer_blocks:
            x = transformer.forward(x, mask)
        
        # x = torch.mean(x, dim = 1)
        x = x.view((x.shape[0], x.shape[1] * x.shape[2]))
        x = self.linear_mapping(x)

        # print(x.shape)
        # x = self.relu(x)
        return x
