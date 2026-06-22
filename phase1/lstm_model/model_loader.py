"""
SEABeacon — Component A: Flood LSTM
model_loader.py

Custom Keras layer/loss definitions (must match the training notebook
EXACTLY, or Keras cannot deserialize the saved .keras file) and the
function that loads the model + all supporting artifacts from ./model/.
"""

import json

import pandas as pd
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers

import config


class LuongAttention(layers.Layer):
    """
    Luong-style attention. Must be byte-for-byte identical to the version
    used when best_model_phase2.keras was trained, or loading will fail.
    """

    def __init__(self, units, **kwargs):
        super().__init__(**kwargs)
        self.units = units
        self.Wq = layers.Dense(units, use_bias=False)
        self.Wk = layers.Dense(units, use_bias=False)

    def call(self, inputs):
        query, values = inputs
        q   = tf.expand_dims(self.Wq(query), 1)
        s   = tf.matmul(q, self.Wk(values), transpose_b=True)
        w   = tf.nn.softmax(s, axis=-1)
        ctx = tf.matmul(w, values)
        return tf.squeeze(ctx, 1), tf.squeeze(w, 1)

    def get_config(self):
        cfg = super().get_config()
        cfg.update({"units": self.units})
        return cfg


def focal_loss(gamma: float = 2.0, alpha: float = 0.85):
    """
    Focal loss used during Phase 2 training to fix the near-zero recall on
    rare flood tiers seen in Phase 1. Must match training exactly.
    """

    def loss_fn(y_true, y_pred):
        y_pred  = tf.clip_by_value(y_pred, 1e-7, 1 - 1e-7)
        bce     = -(y_true * tf.math.log(y_pred) + (1 - y_true) * tf.math.log(1 - y_pred))
        pt      = y_true * y_pred + (1 - y_true) * (1 - y_pred)
        alpha_t = y_true * alpha + (1 - y_true) * (1 - alpha)
        return tf.reduce_mean(alpha_t * (1 - pt) ** gamma * bce)

    return loss_fn


def load_artifacts():
    """
    Loads the trained model + scaler + feature list + basin metadata.

    Returns:
      model         : compiled Keras model, ready for .predict()
      scaler_params : dict keyed by basin_id -> {mean_: [...], scale_: [...]}
      feature_cols  : list of feature column names, in training order
      basins        : list of dicts, one per monitored basin
                       (basin_id, country, lat, lon, flood_cms, provinces, ...)
    """
    print("Loading model and artifacts...")

    if not config.MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Model file not found at {config.MODEL_PATH}\n"
            f"Did you download it from the Kaggle Model and place it in ./model/ ?"
        )

    model = keras.models.load_model(
        str(config.MODEL_PATH),
        custom_objects={
            "LuongAttention": LuongAttention,
            "loss_fn": focal_loss(),
            "focal_loss": focal_loss,
        },
    )

    with open(config.SCALER_PATH) as f:
        scaler_params = json.load(f)

    with open(config.FEATURES_PATH) as f:
        feature_meta = json.load(f)

    basin_df = pd.read_csv(config.BASIN_META_PATH)
    basin_df["provinces"] = basin_df["provinces"].apply(eval)
    basins = basin_df.to_dict("records")

    print(f"  Model loaded. {len(basins)} basins, {feature_meta['n_features']} features")
    return model, scaler_params, feature_meta["feature_cols"], basins
