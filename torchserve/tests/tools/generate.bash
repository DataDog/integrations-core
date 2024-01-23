#!/usr/bin/env bash

rm -f *.mar *.pth

python generate_pth.py -a 1 -b 2 -o 1_2.pth
torch-model-archiver --model-name linear_regression_1_2 --version 1 --model-file model.py --serialized-file 1_2.pth --handler handler.py
mv linear_regression_1_2.mar linear_regression_1_2_v1.mar
python generate_pth.py -a 1 -b 2 -o 1_2.pth
torch-model-archiver --model-name linear_regression_1_2 --version 2 --model-file model.py --serialized-file 1_2.pth --handler handler.py
mv linear_regression_1_2.mar linear_regression_1_2_v2.mar
python generate_pth.py -a 1 -b 2 -o 1_2.pth
torch-model-archiver --model-name linear_regression_1_2 --version 3 --model-file model.py --serialized-file 1_2.pth --handler handler.py
mv linear_regression_1_2.mar linear_regression_1_2_v3.mar

python generate_pth.py -a 2 -b 3 -o 2_3.pth
torch-model-archiver --model-name linear_regression_2_3 --version 1 --model-file model.py --serialized-file 2_3.pth --handler handler.py

python generate_pth.py -a 3 -b 2 -o 3_2.pth
torch-model-archiver --model-name linear_regression_3_2 --version 1 --model-file model.py --serialized-file 3_2.pth --handler handler.py

python generate_pth.py -a 1 -b 1 -o 1_1.pth
torch-model-archiver --model-name linear_regression_1_1 --version 1 --model-file model.py --serialized-file 1_1.pth --handler handler.py

python generate_pth.py -a 2 -b 2 -o 2_2.pth
torch-model-archiver --model-name linear_regression_2_2 --version 1 --model-file model.py --serialized-file 2_2.pth --handler handler.py

python generate_pth.py -a 3 -b 3 -o 3_3.pth
torch-model-archiver --model-name linear_regression_3_3 --version 1 --model-file model.py --serialized-file 3_3.pth --handler handler.py

rm -f ../docker/torchserve/models/*
mv *.mar ../docker/torchserve/models
rm -f *.mar *.pth
