"""
Split fashion dataset into train and test metadata files.

This module processes the fashion dataset to create train/test splits with triplets
(scene, positive product, negative product) for training the recommendation model.
"""

import argparse
import logging
import os
import sys
import time

import numpy as np
import pandas as pd

import config
from utils import utils

# Create logger (will be configured in main())
logger = logging.getLogger(__name__)



def generate_train_test_triplets(scene_product_pairs, num_negative_samples):
    """
    Generate train and test triplets from scene-product pairs.

    Args:
        scene_product_pairs: List of valid scene-product pairs
        num_negative_samples: Number of negative samples per positive pair

    Returns:
        tuple: (train_triplets, test_triplets)
    """
    logger.info("Generating train and test triplets...")
    train_triplets, test_triplets = utils.generate_triplets(
        scene_product_pairs, num_negative_samples
    )

    num_train = len(train_triplets)
    num_test = len(test_triplets)
    logger.info(f"Generated {num_train} train triplets and {num_test} test triplets.")

    return train_triplets, test_triplets


def shuffle_and_convert_to_dataframes(train_triplets, test_triplets):
    """
    Shuffle triplets and convert to pandas DataFrames.

    Args:
        train_triplets: List of training triplets
        test_triplets: List of test triplets

    Returns:
        tuple: (train_df, test_df)
    """
    logger.info("Shuffling triplets and creating DataFrames...")

    # Shuffle the data
    np.random.shuffle(train_triplets)
    np.random.shuffle(test_triplets)

    # Convert to numpy arrays then DataFrames
    train_array = np.array(train_triplets)
    test_array = np.array(test_triplets)

    column_names = ["scene", "positive_product", "negative_product"]
    train_df = pd.DataFrame(train_array, columns=column_names)
    test_df = pd.DataFrame(test_array, columns=column_names)

    return train_df, test_df


def save_metadata_files(train_df, test_df, train_path, test_path):
    """
    Save train and test DataFrames to CSV files.

    Args:
        train_df: Training DataFrame
        test_df: Test DataFrame
        train_path: Path to save training metadata
        test_path: Path to save test metadata
    
    Note:
        Creates parent directories if they don't exist.
    """
    # Ensure parent directories exist
    os.makedirs(os.path.dirname(train_path), exist_ok=True)
    logger.info(f"Saving training metadata to: {train_path}")
    train_df.to_csv(train_path, index=False)

    os.makedirs(os.path.dirname(test_path), exist_ok=True)
    logger.info(f"Saving test metadata to: {test_path}")
    test_df.to_csv(test_path, index=False)

    logger.info("Metadata files saved successfully!")


def main():
    """
    Main function to orchestrate the train/test split process.
    """
    parser = argparse.ArgumentParser(
        description="Split fashion dataset into train/test metadata files"
    )
    parser.add_argument(
        "--log_level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Set logging level",
    )
    parser.add_argument(
        "--log_file",
        help="Log file path (default: split_metadata_YYYYMMDD_HHMMSS_PID.log)",
    )

    args = parser.parse_args()

    # Configure logging with dynamic log file path
    if args.log_file:
        log_file = args.log_file
    else:
        # Create default log file with timestamp and process ID
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        pid = os.getpid()
        log_file = f"split_metadata_{timestamp}_{pid}.log"

    # Setup logging configuration
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
    )

    logger.info("Starting train/test metadata split process...")

    try:
        # Load configuration
        config_obj = config.get_config()

        # Use num_negative_samples from config
        num_negative_samples = config_obj.data.num_negative_samples
        logger.info(f"Using {num_negative_samples} negative samples per positive pair")

        # Set random seed for reproducibility
        utils.set_seed(config_obj)

        # Load scene-product pairs
        scene_product_pairs = utils.get_valid_scene_product(
            config_obj.data.raw_image_path, config_obj.data.metadata_path
        )

        if not scene_product_pairs:
            logger.error("No valid scene-product pairs found. Check your data paths.")
            return 1

        # Generate train/test triplets
        train_triplets, test_triplets = generate_train_test_triplets(
            scene_product_pairs, num_negative_samples
        )

        if not train_triplets or not test_triplets:
            logger.error("Failed to generate triplets. Check your data.")
            return 1

        # Convert to DataFrames
        train_df, test_df = shuffle_and_convert_to_dataframes(
            train_triplets, test_triplets
        )

        # Save to CSV files
        save_metadata_files(
            train_df,
            test_df,
            config_obj.data.metatrain_path,
            config_obj.data.metatest_path,
        )

        # Validate output files
        if os.path.exists(config_obj.data.metatrain_path) and os.path.exists(
            config_obj.data.metatest_path
        ):
            logger.info("Process completed successfully!")
            logger.info(f"Train samples: {len(train_df)}")
            logger.info(f"Test samples: {len(test_df)}")
            return 0
        else:
            logger.error("Output files were not created successfully")
            return 1

    except Exception as e:
        logger.error(f"An error occurred during processing: {str(e)}")
        logger.exception("Full traceback:")
        return 1


if __name__ == "__main__":
    sys.exit(main())
