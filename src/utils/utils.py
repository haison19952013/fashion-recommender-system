import json
import os
import random
from typing import List, Tuple

import numpy as np


def is_valid_file(fname: str) -> bool:
    """Check if file exists and is not empty.
    
    Args:
        fname: Path to the file to check.
        
    Returns:
        True if file exists and has content, False otherwise.
    """
    return os.path.exists(fname) and os.path.getsize(fname) > 0


def id_to_filename(image_dir: str, id: str) -> str:
    """Convert image ID to full file path.
    
    Args:
        image_dir: Directory containing image files.
        id: Image identifier without extension.
        
    Returns:
        Full path to the image file.
    """
    filename = os.path.join(image_dir, id + ".jpg")
    return filename


def key_to_url(key: str) -> str:
    """
    Converts a pinterest hex key into a url.

    Args:
        key: Pinterest hexadecimal key (must be at least 6 characters)

    Returns:
        Pinterest image URL

    Raises:
        ValueError: If key is too short or invalid format
    """
    if not key or len(key) < 6:
        raise ValueError(f"Pinterest key must be at least 6 characters, got: {key}")

    if not all(c in "0123456789abcdefABCDEF" for c in key):
        raise ValueError(f"Pinterest key must be hexadecimal, got: {key}")

    prefix = "https://i.pinimg.com/400x/%s/%s/%s/%s.jpg"
    return prefix % (key[0:2], key[2:4], key[4:6], key)


def set_seed(config) -> None:
    """Set random seed for reproducibility.
    
    Args:
        config: Configuration object with optional 'seed' attribute.
    """
    random_seed = getattr(config, "seed", None)
    if random_seed is not None:
        random.seed(random_seed)
        np.random.seed(random_seed)


def get_valid_scene_product(
    image_dir: str, input_file: str
) -> List[List[str]]:
    """Load valid scene-product pairs from JSON file.
    
    Args:
        image_dir: Directory containing image files.
        input_file: Path to JSON file with scene-product mappings.
        
    Returns:
        List of [scene_path, product_path] pairs for valid files.
    """
    scene_product = []
    with open(input_file, "r") as f:
        data = f.readlines()
        for line in data:
            row = json.loads(line)
            scene = id_to_filename(image_dir, row["scene"])
            product = id_to_filename(image_dir, row["product"])
            if is_valid_file(scene) and is_valid_file(product):
                scene_product.append([scene, product])
    return scene_product

def generate_triplets(
    scene_product: List[List[str]],
    num_neg: int
) -> Tuple[List[Tuple[str, str, str]], List[Tuple[str, str, str]]]:
    """Generate train/test triplets with negative samples.
    
    Args:
        scene_product: List of [scene_path, product_path] pairs.
        num_neg: Number of negative samples per positive pair.
        
    Returns:
        Tuple of (train_triplets, test_triplets) where each triplet is
        (scene, positive_product, negative_product).
    """
    count = len(scene_product)
    train = []
    test = []
    for i in range(count):
        scene, pos = scene_product[i]
        is_test = i % 10 == 0
        neg_indices = np.random.randint(0, count, num_neg)
        for neg_idx in neg_indices:
            # Ensure negative sample is not the same as the positive sample
            if neg_idx == i:
                new_neg_idx = np.random.randint(0, count)
                while new_neg_idx == i:
                    new_neg_idx = np.random.randint(0, count)
                neg_idx = new_neg_idx
            _, neg = scene_product[neg_idx]
            if is_test:
                test.append((scene, pos, neg))
            else:
                train.append((scene, pos, neg))
    return train, test
