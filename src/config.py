from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class DataConfig:
    """Data-related configuration."""

    metadata_path: str = "data/fashion.json"
    raw_image_path: str = "data/fashion_images_v0"
    num_negative_samples: int = 5
    metatrain_path: str = "data/meta_train.csv"
    metatest_path: str = "data/meta_test.csv"
    scene_embed_path: str = "embedding_data/scene_embed.json"
    product_embed_path: str = "embedding_data/product_embed.json"


@dataclass
class TrainConfig:
    """Training-related configuration."""

    learning_rate: float = 0.0001618 # Optimal: 0.0001618
    regularization: float = 0.2076 # Optimal: 0.2076
    embedding_dim: int = 64 # Optimal: 64
    batch_size: int = 32
    log_every_steps: int = 100
    eval_every_steps: int = 100
    checkpoint_every_steps: int = 5000
    max_steps: int = 30000
    work_dir: str = "./tmp"
    model_name: str = "recsys-fashion-model"
    restore_checkpoint: bool = True
    mlflow_experiment_name: str = "recsys-fashion-experiment"


@dataclass
class Config:
    """Main configuration class."""

    seed: int = 42
    environment: str = "development"
    data: DataConfig = field(default_factory=DataConfig)
    train: TrainConfig = field(default_factory=TrainConfig)

    def validate(self) -> None:
        """Validate configuration values."""
        assert self.seed >= 0, "Seed must be non-negative"
        assert self.train.learning_rate > 0, "Learning rate must be positive"
        assert self.train.batch_size > 0, "Batch size must be positive"
        assert self.train.embedding_dim > 0, "Embedding dimension must be positive"
        assert self.data.num_negative_samples >= 0, (
            "Number of negative samples must be non-negative"
        )

        # Validate paths exist if in production
        if self.environment == "production":
            assert Path(self.data.metadata_path).exists(), (
                f"Metadata path not found: {self.data.metadata_path}"
            )
            assert Path(self.data.raw_image_path).exists(), (
                f"Raw image path not found: {self.data.raw_image_path}"
            )


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get global config instance."""
    global _config
    if _config is None:
        _config = Config()
        _config.validate()  # Validate on first creation
    return _config


if __name__ == "__main__":
    config = get_config()
    print(config.data)