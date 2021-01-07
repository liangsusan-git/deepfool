import os
import toml
import random
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import torch.utils.data as Data
import torch.backends.cudnn as cudnn
from tensorboardX import SummaryWriter

import data
from model import DF
from utils import *

def main(config_path):
    cudnn.benchmark = True

    config = toml.load(config_path)
    writer = SummaryWriter("runs/poker")

    # model
    model_crt  = DF()
    model_last = DF()

    # resume from a checkpoint
    if config["model"]["load"]:
        checkpoint = torch.load(config["general"]["load_path"])
        model_crt.load_state_dict(checkpoint['model'])
        model_last.load_state_dict(checkpoint['model'])
        print("successfully load model")

    model_crt.cuda()
    #model = nn.DataParallel(model)


    # data
    dataloader_train = data.POKER_DATASET(model_last)

    # criterion
    criterion = nn.L1Loss()

    # optim
    params = [
        {"params": model_crt.parameters(), "lr": config["hyperparameters"]["lr"]}
    ]
    optimizer = optim.Adam(params, betas=(config["hyperparameters"]["betas"], 0.999), weight_decay=config["hyperparameters"]["decay"])
    lr_scheduler = optim.lr_scheduler.ExponentialLR(optimizer, gamma=0.9)

    for epoch in range(config["general"]["start_epoch"], config["general"]["start_epoch"] + config["general"]["epochs"]):
        train_package = [
            dataloader_train,
            model_crt,
            criterion,
            optimizer,
            lr_scheduler,
            writer,
            config,
            epoch
        ]
        train(train_package)

        if (epoch + 1) % config["model"]["save_iter"] == 0:
            save_checkpoint({
                "model": model_crt.state_dict(),
            }, config["general"]["save_path"] + "checkpoint_{}.pt".format(epoch+1))

        model_last.load_state_dict(model_crt.state_dict().cpu())

        #lr_scheduler.step(epoch-config["general"]["start_epoch"])

def train(package):
    [dataloader, 
     model, 
     criterion, 
     optimizer, 
     lr_scheduler,
     writer,
     config,
     epoch] = package

    model.train()
    feature, label = dataloader.__next__()
    feature = feature.cuda()
    label = label.cuda()
    predict = model(feature)
    loss = criterion(predict, label)
    loss.backward()
    optimizer.step()
    optimizer.zero_grad()

    if epoch % 10 == 0:
        print("epoch: {} iteration: {}/{} loss: {:.6f}".format(epoch + 1, i, length, loss))
        writer.add_scalars("train loss", {"sum": loss}, i + epoch * length)

if __name__ == "__main__":
    main("./train.toml")