import httpx
from core.config import settings
import uuid

async def upload_to_supabase(file_content: bytes, filename: str, bucket: str = "resumes") -> str:
    """
    Uploads a file to Supabase storage and returns the public URL.
    """
    supabase_url = settings.NEXT_PUBLIC_SUPABASE_URL
    supabase_key = settings.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY
    
    if not supabase_url or not supabase_key:
        print("Supabase URL or Key not configured. Skipping upload.")
        return ""

    # Ensure URL is clean
    base_url = supabase_url.rstrip('/')
    
    # Supabase Storage API endpoint
    # POST /storage/v1/object/{bucket}/{path}
    unique_filename = f"{uuid.uuid4()}_{filename}"
    upload_url = f"{base_url}/storage/v1/object/{bucket}/{unique_filename}"
    
    headers = {
        "Authorization": f"Bearer {supabase_key}",
        "apikey": supabase_key,
        "Content-Type": "application/pdf" if filename.endswith(".pdf") else "application/octet-stream"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(upload_url, content=file_content, headers=headers)
        
        if response.status_code == 200:
            # Construct public URL
            # https://{project}.supabase.co/storage/v1/object/public/{bucket}/{path}
            public_url = f"{base_url}/storage/v1/object/public/{bucket}/{unique_filename}"
            return public_url
        else:
            print(f"Failed to upload to Supabase: {response.status_code} - {response.text}")
            return ""
