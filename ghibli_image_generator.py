from gradio_client import Client, handle_file
import time
from tqdm import tqdm
import os
from dotenv import load_dotenv
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

def generate_ghibli_image(
    prompt="Ghibli Studio style, Charming hand-drawn anime-style illustration",
    image_url="9bce8a119b0ff1b7038f86e7a7d41373.jpg",
    height=768,
    width=768,
    seed=42,
    control_type="Ghibli",
    max_retries=3,
    queue_timeout=180,
    hf_token=None,
    progress_callback=None
):
    """
    Generate a Ghibli-style image using the EasyControl_Ghibli API.
    
    Args:
        prompt (str): The text prompt describing the desired image
        image_url (str): URL or path of the input image to transform
        height (int): Height of the output image
        width (int): Width of the output image
        seed (int): Random seed for reproducibility
        control_type (str): Type of control (default: "Ghibli")
        max_retries (int): Maximum number of retry attempts
        queue_timeout (int): Maximum time to wait in queue (seconds)
        hf_token (str, optional): Hugging Face API token for authentication
        progress_callback (callable, optional): Function to call with progress updates
    
    Returns:
        dict: The generated image data or None if failed
    """
    token = hf_token or os.getenv('HUGGING_FACE_TOKEN')
    
    if not token:
        logger.error("No Hugging Face token provided")
        raise ValueError("Hugging Face token is required")
        
    if not os.path.isfile(image_url):
        logger.error(f"Input image not found: {image_url}")
        raise FileNotFoundError(f"Input image not found: {image_url}")
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Attempt {attempt + 1}/{max_retries}")
            
            client = Client(
                "jamesliu1217/EasyControl_Ghibli",
                hf_token=token
            )
            
            if progress_callback:
                progress_callback(10)  # Connection established
            
            logger.info("Sending request to API...")
            try:
                with open(image_url, 'rb') as img_file:
                    result = client.predict(
                        prompt=prompt,
                        spatial_img=handle_file(image_url),
                        height=height,
                        width=width,
                        seed=seed,
                        control_type=control_type,
                        api_name="/single_condition_generate_image"
                    )
                
                if progress_callback:
                    progress_callback(100)
                
                logger.info("Image generated successfully")
                return result
                
            except Exception as e:
                error_msg = str(e)
                logger.error(f"API error: {error_msg}")
                
                if "No GPU was available" in error_msg:
                    if progress_callback:
                        progress_callback(-1)  # Indicate retry
                    logger.info("No GPU available, retrying...")
                    time.sleep(5)
                    continue
                    
                if "not found" in error_msg.lower():
                    raise ValueError("Invalid API endpoint or model not found")
                    
                raise e
                    
        except Exception as e:
            logger.error(f"Error in attempt {attempt + 1}: {str(e)}")
            if attempt == max_retries - 1:
                logger.error("Max retries reached")
                raise RuntimeError(f"Failed after {max_retries} attempts: {str(e)}")
            time.sleep(5)
    
    return None

if __name__ == "__main__":
    logger.info("Starting Ghibli Image Generator...")
    
    try:
        result = generate_ghibli_image()
        if result:
            logger.info("Image generated successfully!")
            logger.info(f"Output: {result}")
        else:
            logger.error("Failed to generate image after all attempts.")
    except Exception as e:
        logger.error(f"Error: {str(e)}") 