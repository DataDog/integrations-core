# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import argparse

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from model import ManualLinearRegression
from torch.utils.data import DataLoader, Dataset, TensorDataset
from torch.utils.data.dataset import random_split

argParser = argparse.ArgumentParser()
argParser.add_argument("-a", help="value for a", default=1, type=int)
argParser.add_argument("-b", help="value for b", default=2, type=int)
argParser.add_argument("-o", help="output file name", default="model.pth", type=str)

args = argParser.parse_args()

device = 'cuda' if torch.cuda.is_available() else 'cpu'

np.random.seed(42)
x = np.random.rand(100, 1)
true_a, true_b = args.a, args.b
rand = np.random.randn(100, 1)

# y = a + bx + epsilon
y = true_a + true_b * x + 0.1 * rand

# Create the tensors
x_tensor = torch.from_numpy(x).float()
y_tensor = torch.from_numpy(y).float()


class CustomDataset(Dataset):
    def __init__(self, x_tensor, y_tensor):
        self.x = x_tensor
        self.y = y_tensor

    def __getitem__(self, index):
        return (self.x[index], self.y[index])

    def __len__(self):
        return len(self.x)


dataset = TensorDataset(x_tensor, y_tensor)  # dataset = CustomDataset(x_tensor, y_tensor)

# Split the dataset into two
train_dataset, val_dataset = random_split(dataset, [80, 20])

train_loader = DataLoader(dataset=train_dataset, batch_size=16)
val_loader = DataLoader(dataset=val_dataset, batch_size=20)


def make_train_step(model, loss_fn, optimizer):
    def train_step(x, y):
        model.train()
        yhat = model(x)
        loss = loss_fn(y, yhat)
        loss.backward()
        optimizer.step()
        optimizer.zero_grad()
        return loss.item()

    return train_step


# Estimate a and b
torch.manual_seed(42)

model = ManualLinearRegression().to(device)  # model = nn.Sequential(nn.Linear(1, 1)).to(device)
loss_fn = nn.MSELoss(reduction='mean')
optimizer = optim.SGD(model.parameters(), lr=1e-1)
train_step = make_train_step(model, loss_fn, optimizer)

n_epochs = 100
training_losses = []
validation_losses = []

# Train the model
for _epoch in range(n_epochs):
    batch_losses = []
    for x_batch, y_batch in train_loader:
        x_batch = x_batch.to(device)
        y_batch = y_batch.to(device)
        loss = train_step(x_batch, y_batch)
        batch_losses.append(loss)
    training_loss = np.mean(batch_losses)
    training_losses.append(training_loss)

    with torch.no_grad():
        val_losses = []
        for x_val, y_val in val_loader:
            x_val = x_val.to(device)
            y_val = y_val.to(device)
            model.eval()
            yhat = model(x_val)
            val_loss = loss_fn(y_val, yhat).item()
            val_losses.append(val_loss)
        validation_loss = np.mean(val_losses)
        validation_losses.append(validation_loss)

# Save the trained model
torch.save(model.state_dict(), args.o)
