import argparse
import json
import logging
import os
import time
from typing import FrozenSet

import requests

from utils import utils

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('crawl_data.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def get_keys(input_file: str, max_lines: int) -> FrozenSet[str]:
    """
    Reads in the Shop the look json file and returns a set of keys.
    
    Args:
        input_file: Path to the input JSON file
        max_lines: Maximum number of lines to process
        
    Returns:
        FrozenSet of unique keys found in the file
        
    Raises:
        FileNotFoundError: If input file doesn't exist
        json.JSONDecodeError: If JSON parsing fails
    """
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"Input file not found: {input_file}")
    
    logger.info(f"Reading keys from {input_file}, max lines: {max_lines}")
    keys = []
    
    try:
        with open(input_file, "r", encoding='utf-8') as f:
            for count, line in enumerate(f, 1):
                if count > max_lines:
                    break
                    
                try:
                    row = json.loads(line.strip())
                    if "product" in row:
                        keys.append(row["product"])
                    if "scene" in row:
                        keys.append(row["scene"])
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse JSON on line {count}: {e}")
                    continue
                    
                if count % 1000 == 0:
                    logger.info(f"Processed {count} lines, found {len(set(keys))} unique keys")
                    
    except Exception as e:
        logger.error(f"Error reading file {input_file}: {e}")
        raise
    
    unique_keys = frozenset(keys)
    logger.info(f"Found {len(unique_keys)} unique keys from {count} lines")
    return unique_keys

def fetch_image(key: str, output_dir: str, base_sleep_time: float, max_retries: int = 5) -> bool:
    """
    Fetches an image from Pinterest.
    
    Args:
        key: Pinterest image key
        output_dir: Directory to save the image
        base_sleep_time: Base sleep time between retries
        max_retries: Maximum number of retry attempts
        
    Returns:
        True if image was newly downloaded, False if already exists or failed
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
        
    output_name = os.path.join(output_dir, f"{key}.jpg")
    if os.path.exists(output_name):
        logger.debug(f"{key} already downloaded")
        return False

    url = utils.key_to_url(key)
    logger.debug(f"Fetching image: {url}")
    
    # Set proper headers to avoid being blocked
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Referer': 'https://www.pinterest.com/',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            # Validate content type
            content_type = response.headers.get('content-type', '').lower()
            if not content_type.startswith('image/'):
                logger.warning(f"Unexpected content type for {key}: {content_type}")
                return False
            
            with open(output_name, "wb") as f:
                f.write(response.content)
            
            logger.debug(f"Successfully downloaded {key}")
            return True
            
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout for {key}, attempt {attempt + 1}/{max_retries}")
        except requests.exceptions.RequestException as e:
            logger.warning(f"Network error for {key}, attempt {attempt + 1}/{max_retries}: {e}")
        except IOError as e:
            logger.error(f"File write error for {key}: {e}")
            return False
        
        if attempt < max_retries - 1:
            sleep_time = base_sleep_time * (2 ** attempt)  # Exponential backoff
            logger.debug(f"Sleeping {sleep_time}s before retry")
            time.sleep(sleep_time)
    
    logger.error(f"Failed to download {key} after {max_retries} attempts")
    return False

def main():
    """Main function to orchestrate the image crawling process."""
    parser = argparse.ArgumentParser(description="Fetch images from Pinterest")
    parser.add_argument("--input_file", required=True, help="Input json file")
    parser.add_argument("--max_lines", type=int, default=100000, help="Max lines to read")
    parser.add_argument("--sleep_time", type=float, default=1.0, help="Base sleep time between requests")
    parser.add_argument("--batch_sleep", type=float, default=5.0, help="Sleep time between batches")
    parser.add_argument("--batch_size", type=int, default=50, help="Number of images per batch")
    parser.add_argument("--output_dir", required=True, help="Output directory for images")
    parser.add_argument("--max_retries", type=int, default=3, help="Max retry attempts per image")
    parser.add_argument("--log_level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                       help="Set logging level")
    
    args = parser.parse_args()
    
    # Set logging level
    logger.setLevel(getattr(logging, args.log_level))
    
    # Validate arguments
    if args.max_lines <= 0:
        raise ValueError("max_lines must be positive")
    if args.sleep_time < 0:
        raise ValueError("sleep_time cannot be negative")
    if args.batch_size <= 0:
        raise ValueError("batch_size must be positive")
    
    logger.info("Starting image crawling process")
    logger.info(f"Input file: {args.input_file}")
    logger.info(f"Output directory: {args.output_dir}")
    logger.info(f"Max lines: {args.max_lines}")
    
    try:
        # Get keys from input file
        keys = get_keys(args.input_file, args.max_lines)
        total_keys = len(keys)
        keys = sorted(keys)
        logger.info(f"Found {total_keys} unique images to fetch")
        
        if total_keys == 0:
            logger.warning("No keys found to process")
            return
        
        # Process images
        downloaded_count = 0
        skipped_count = 0
        failed_count = 0
        start_time = time.time()
        
        for i, key in enumerate(keys, 1):
            try:
                result = fetch_image(key, args.output_dir, args.sleep_time, args.max_retries)
                if result:
                    downloaded_count += 1
                else:
                    if os.path.exists(os.path.join(args.output_dir, f"{key}.jpg")):
                        skipped_count += 1
                    else:
                        failed_count += 1
                
                # Progress reporting
                if i % 100 == 0 or i == total_keys:
                    elapsed = time.time() - start_time
                    rate = i / elapsed if elapsed > 0 else 0
                    logger.info(f"Progress: {i}/{total_keys} ({i/total_keys*100:.1f}%), "
                              f"Downloaded: {downloaded_count}, Skipped: {skipped_count}, "
                              f"Failed: {failed_count}, Rate: {rate:.2f} images/sec")
                
                # Batch sleep
                if downloaded_count > 0 and downloaded_count % args.batch_size == 0:
                    logger.info(f"Batch complete, sleeping for {args.batch_sleep}s")
                    time.sleep(args.batch_sleep)
                elif result:  # Only sleep if we actually downloaded something
                    time.sleep(args.sleep_time)
                    
            except KeyboardInterrupt:
                logger.info("Interrupted by user")
                break
            except Exception as e:
                logger.error(f"Unexpected error processing {key}: {e}")
                failed_count += 1
                continue
        
        # Final statistics
        total_time = time.time() - start_time
        logger.info("\n" + "="*50)
        logger.info("CRAWLING COMPLETE")
        logger.info(f"Total processed: {i}")
        logger.info(f"Downloaded: {downloaded_count}")
        logger.info(f"Skipped (already exists): {skipped_count}")
        logger.info(f"Failed: {failed_count}")
        logger.info(f"Total time: {total_time:.2f}s")
        logger.info(f"Average rate: {i/total_time:.2f} images/sec")
        logger.info("="*50)
        
    except Exception as e:
        logger.error(f"Fatal error in main process: {e}")
        raise

if __name__ == "__main__":
    main()