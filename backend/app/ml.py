
def load(self) -> None:
    s = self.settings

    try:
        from huggingface_hub import hf_hub_download
        import keras

        # Download the complete model from Hugging Face
        repo_id = os.getenv(
            "HF_MODEL_REPO",
            "Lockey815/LeukNet-ResNet50"
        )

        filename = os.getenv(
            "HF_MODEL_FILENAME",
            "resnet50_final.keras"
        )

        token = os.getenv("HF_TOKEN") or None

        log.info("Downloading model from Hugging Face: %s", repo_id)

        model_path = hf_hub_download(
            repo_id=repo_id,
            filename=filename,
            repo_type="model",
            token=token,
        )

        log.info("Model downloaded: %s", model_path)

        # Load the complete Keras model
        model = keras.models.load_model(
            model_path,
            compile=False,
        )

        # Read model input and output dimensions
        ishape = model.input_shape
        self.input_h = int(ishape[1])
        self.input_w = int(ishape[2])

        n_out = int(model.output_shape[-1])

        if n_out != len(s.class_list):
            raise ValueError(
                f"Model has {n_out} outputs but "
                f"CLASS_NAMES lists {len(s.class_list)}."
            )

        if not 0 <= s.blast_class_index < n_out:
            raise ValueError(
                "BLAST_CLASS_INDEX is out of range for this model."
            )

        # Load optional local metadata
        meta_path = s.resolve(s.model_metadata_path)
        meta = {}

        if meta_path.exists():
            meta = json.loads(
                meta_path.read_text(encoding="utf-8")
            )

        self.info = {
            "name": model.name or "LeukNet",
            "input_size": [self.input_h, self.input_w],
            "classes": s.class_list,
            "blast_class": s.class_list[s.blast_class_index],
            "preprocess_mode": s.preprocess_mode,
            "blast_probability_threshold": s.blast_prob_threshold,
            "keras_version": meta.get("keras_version"),
            "model_saved": meta.get("date_saved"),
            "source": f"huggingface:{repo_id}/{filename}",
        }

        self.model = model
        self.error = None

        # Warm-up inference
        self.model.predict(
            np.zeros(
                (1, self.input_h, self.input_w, 3),
                dtype=np.float32
            ),
            verbose=0,
        )

        log.info("LeukNet model loaded successfully: %s", self.info)

    except Exception as exc:
        self.model = None
        self.error = f"{type(exc).__name__}: {exc}"
        log.exception("Model failed to load")
