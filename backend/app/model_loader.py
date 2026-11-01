import os

import keras
from huggingface_hub import hf_hub_download


MODEL_REPO = "Lockey815/LeukNet-ResNet50"
MODEL_FILENAME = "resnet50_final.keras"


def load_leuknet_model():
    print("Downloading LeukNet model from Hugging Face...")

    model_path = hf_hub_download(
        repo_id=MODEL_REPO,
        filename=MODEL_FILENAME,
        repo_type="model",
    )

    print(f"Model downloaded to: {model_path}")
    print("Loading LeukNet model...")

    model = keras.models.load_model(
        model_path,
        compile=False,
    )

    print("LeukNet model loaded successfully.")
    return model
