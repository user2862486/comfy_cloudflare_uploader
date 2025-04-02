import os
import io
import requests
import json
from PIL import Image
import numpy as np
import torch

class CloudflareImageUploader:
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
        """
        if not account_id or not api_token:
            print("Warning: Cloudflare credentials not provided. Images will not be uploaded.")
            return (images, "")
        
        cloudflare_ids = []
        
        for i in range(images.shape[0]):
            # Convert image tensor to PIL Image
            img = tensor2pil(images[i])
            
            # Convert PIL Image to bytes
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            
            # Create a unique filename
            filename = f"{filename_prefix}_{i}.png"
            
            # Upload to Cloudflare
            try:
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
                        error = result.get('errors', ['Unknown error'])
                        print(f"Error uploading to Cloudflare: {error}")
                else:
                    print(f"Upload failed with status {response.status_code}")
            
            except Exception as e:
                print(f"Error uploading to Cloudflare: {e}")
        
        # Special format for ComfyUI's node execution system
        # Returns: (images, IDs)
        return {
            "ui": {
                "cloudflare_ids": cloudflare_ids
            },
            "result": (images, json.dumps(cloudflare_ids) if len(cloudflare_ids) > 1 else cloudflare_ids[0] if cloudflare_ids else "")
        }

# Helper function to convert tensor to PIL Image
def tensor2pil(image):
    """Convert a PyTorch tensor to a PIL Image."""
    # Convert tensor to numpy array
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
