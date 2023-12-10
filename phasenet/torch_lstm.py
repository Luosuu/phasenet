# FashionMnist VQ experiment with various settings.
# From https://github.com/minyoungg/vqtorch/blob/main/examples/autoencoder.py

from tqdm.auto import trange

import torch
import torch.nn as nn
from torchvision import datasets, transforms
from torch.utils.data import DataLoader
from transformers import (
    CONFIG_MAPPING,
    MODEL_FOR_CAUSAL_LM_MAPPING,
    BitsAndBytesConfig,
    AutoConfig,
    AutoModelForCausalLM,
    AutoTokenizer,
    HfArgumentParser,
    Trainer,
    TrainingArguments,
    default_data_collator,
    is_torch_tpu_available,
    set_seed,
)
from vector_quantize_pytorch import VectorQuantize
from seismic_dataset import SeismicDataset
from rinas.hf.mlm_modules import *
from accelerate import Accelerator
from huggingface_hub import login
from torch_vqvae import SimpleVQAutoEncoder, train
from postprocess import extract_picks

if __name__ == '__main__':

    
    lr = 3e-4
    train_iter = 1000
    num_codes = 256
    seed = 1234
    batch_size = 20
    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    data_dir = './dataset/waveform_train/'  
    data_list = './dataset/waveform.csv'


    dataset = SeismicDataset(data_dir = data_dir, data_list = data_list, transform=None)

    train_loader = DataLoader(
        dataset=dataset,
        batch_size=batch_size,
        shuffle=True,
    )

    

    print("training VQ-VAE")
    torch.random.manual_seed(seed)
    model = SimpleVQAutoEncoder(codebook_size=num_codes).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=lr)
    train(model, train_loader, opt, device, train_iterations=train_iter)


    print("Train a LSTM basline")

    model_lm = torch.nn.LSTM(input_size = 2251, hidden_size=128, num_layers=2, batch_first=True)
    
    optimizer = torch.optim.AdamW(model_lm.parameters(), lr=lr)

    model_lm = model_lm.to(device)

    def iterate_dataset(data_loader):
        data_iter = iter(data_loader)
        while True:
            try:
                x, y = next(data_iter)
            except StopIteration:
                data_iter = iter(data_loader)
                x, y = next(data_iter)
            yield x.to(device), y.to(device)

    for _ in (pbar := trange(train_iter)):
        optimizer.zero_grad()
        x, y = next(iterate_dataset(train_loader))
        x = x.permute(0, 3, 1, 2)
        y = y.permute(0, 3, 1, 2)
        # all_ones = y.all(dim=1)
        # label = all_ones.squeeze(-1).to(torch.float32)
        # print(label)
        # print(label.shape)
        # for i in range(label.shape[0]):  # result.shape[0] is 20
        #     # Find indices where the value is 1 in the ith row
        #     indices = (label[i] == 1).nonzero(as_tuple=True)[0]
            
        #     # Print the indices for the ith row
        #     print(f"Row {i}: Indices with value 1: {indices.tolist()}") # empty now??

        out, indices, cmt_loss = model.encode(x)
        print(out.shape)
        out = out.squeeze()
        outputs = model_lm(out)
        loss = outputs.loss
        accelerator.backward(loss)
        optimizer.step()
        pbar.set_description(
            f"loss: {loss.item():.3f} | "
        )