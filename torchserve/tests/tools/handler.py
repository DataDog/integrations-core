# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import torch
from ts.torch_handler.base_handler import BaseHandler


class ModelHandler(BaseHandler):
    def preprocess(self, data):
        return torch.as_tensor([data[0]["body"]["input"]], device=self.device)
