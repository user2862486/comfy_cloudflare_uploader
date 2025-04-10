import os
import io
import requests
import json
from PIL import Image
import numpy as np
import torch

class CloudflareImageUploader:
    """
    ComfyUI node for uploading images directly to Cloudflare Images service.
    All image processing happens in memory without saving to disk.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "account_id": ("STRING", {"default": os.environ.get("CF_ACCOUNT_ID", "")}),
                "api_token": ("STRING", {"default": os.environ.get("CF_API_TOKEN", "")}),
                "filename_prefix": ("STRING", {"default": "ComfyUI"}),
            }
        }
    
    RETURN_TYPES = ("IMAGE", "STRING",)
    RETURN_NAMES = ("images", "cloudflare_id",)
    FUNCTION = "upload_images"
    OUTPUT_NODE = True
    CATEGORY = "image"

    def upload_images(self, images, account_id, api_token, filename_prefix="ComfyUI"):
        """
        Upload images directly to Cloudflare Images and return the image IDs.
        All operations are performed in memory without saving to disk.
        
        Args:
            images: Tensor of images from ComfyUI
            account_id: Cloudflare account ID
            api_token: Cloudflare API token
            filename_prefix: Prefix for the filename shown in Cloudflare (not an actual file path)
            
        Returns:
            Tuple containing the original images and the Cloudflare image IDs
        """
        if not account_id or not api_token:
            print("Warning: Cloudflare credentials not provided. Images will not be uploaded.")
            return (images, "")
        
        if images.shape[0] == 0:
            print("Warning: No images received for upload.")
            return (images, "")
        
        cloudflare_ids = []
        
        for i in range(images.shape[0]):
            try:
                # Convert image tensor to PIL Image (in memory)
                img = tensor2pil(images[i])
                
                # Convert PIL Image to bytes (in memory buffer)
                img_bytes = io.BytesIO()
                img.save(img_bytes, format='PNG')
                img_bytes.seek(0)
                
                # Create a display filename (not an actual file path)
                filename = f"{filename_prefix}_{i}.png"
                
                # Upload bytes directly to Cloudflare
                url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/images/v1"
                headers = {
                    "Authorization": f"Bearer {api_token}"
                }
                files = {
                    'file': (filename, img_bytes, 'image/png')
                }
                
                response = requests.post(url, headers=headers, files=files)
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get('success'):
                        image_id = result['result']['id']
                        cloudflare_ids.append(image_id)
                        print(f"Uploaded image to Cloudflare, ID: {image_id}")
                    else:
                        errors = result.get('errors', [{'message': 'Unknown error'}])
                        error_messages = [e.get('message', str(e)) for e in errors]
                        print(f"Error uploading to Cloudflare: {', '.join(error_messages)}")
                else:
                    print(f"Upload failed with status {response.status_code}: {response.text}")
            
            except Exception as e:
                print(f"Error uploading to Cloudflare: {str(e)}")
        
        # Return format for ComfyUI's node execution system
        return {
            "ui": {
                "cloudflare_ids": cloudflare_ids
            },
            "result": (images, json.dumps(cloudflare_ids) if len(cloudflare_ids) > 1 else cloudflare_ids[0] if cloudflare_ids else "")
        }


def tensor2pil(image):
    """
    Convert a PyTorch tensor to a PIL Image in memory.
    
    Args:
        image: PyTorch tensor representing an image
        
    Returns:
        PIL Image object
    """
    # Convert tensor to numpy array (in memory)
    i = 255. * image.cpu().numpy()
    img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))
    return img


# Node class mappings for ComfyUI to register this node
NODE_CLASS_MAPPINGS = {
    "CloudflareImageUploader": CloudflareImageUploader
}

# Display names for the UI
NODE_DISPLAY_NAME_MAPPINGS = {
    "CloudflareImageUploader": "Cloudflare Image Uploader"
}
