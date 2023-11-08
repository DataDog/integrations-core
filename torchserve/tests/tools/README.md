# Installation and deployment 

To re-generate the models and install them: 

1. Install the requirements with `pip install -r requirements.txt`
2. Run the `generate.bash` script.

It will recreate the *.mar files that are mounted inside the docker container.

# The model

The model is a linear regression using this formula: `y = a + b * x + epsilon`.

The `generate_pth.py` file takes the value of `a` and `b` you want. It will generate a random value for epsilon and train the model to try to approximate as much as possible the real values of a and b you used. 

Once trained, we create a `.pth` file which will contain the information of the trained model. This file can then be loaded in order to run predictions.

This `.pth` file is included in a `.mar` along with other files to be served by TorchServe through its API. 

Note: `.pth` file are not stored in this repository, we only keep the final `.mar` file.

# Generate traffic in the e2e environment

The `generate_traffic.py` file is a simple script that will continuously send requests to the torchserve instance to generate more metrics and logs.
