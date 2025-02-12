from typing import List
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
import openai
import os
import boto3
from botocore.exceptions import ClientError
import uuid

from api.core.auth import get_current_user
from utils.colors import RESET, RED

router = APIRouter(tags=["voice"])

# Initialize S3 client
s3_client = boto3.client(
    's3',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
)
BUCKET_NAME = os.getenv('AWS_BUCKET_NAME')

@router.post("/transcribe")
async def transcribe_audio(
    audio: UploadFile = File(..., description="The audio file to transcribe"),
    current_user: str = Depends(get_current_user)
):
    """Transcribe audio file using OpenAI Whisper API"""
    print("Function called")
    print(f"Request received for user: {current_user}")
    
    try:
        if not audio:
            raise HTTPException(status_code=400, detail="No audio file provided")
            
        print(f"Received file: {audio.filename}, content_type: {audio.content_type}")
        # Read the audio file
        contents = await audio.read()
        
        # Save temporarily
        temp_path = f"temp_{audio.filename}"
        with open(temp_path, "wb") as f:
            f.write(contents)
        
        try:
            # Initialize OpenAI client
            client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            
            # Transcribe using OpenAI Whisper
            with open(temp_path, "rb") as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file
                )
            
            return {"text": transcript.text}
            
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
    except Exception as e:
        print(f"{RED}Error in transcription:\n{str(e)}\n{type(e)}\n{RESET}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/text-to-speech")
async def text_to_speech(
    request: dict,
    current_user: str = Depends(get_current_user)
):
    """Convert text to speech using OpenAI's TTS API and return a URL"""
    try:
        if not request.get("text"):
            raise HTTPException(status_code=400, detail="No text provided")

        # Initialize OpenAI client
        client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

        # Convert text to speech using OpenAI's TTS
        response = client.audio.speech.create(
            model="tts-1", # or "tts-1-hd" for higher quality
            voice="alloy", # can be alloy, echo, fable, onyx, nova, or shimmer
            input=request["text"]
        )

        # Generate unique filename
        filename = f"tts/{current_user}/{uuid.uuid4()}.mp3"

        # Upload to S3
        try:
            s3_client.put_object(
                Bucket=BUCKET_NAME,
                Key=filename,
                Body=response.content,
                ContentType='audio/mpeg'
            )

            # Generate presigned URL that expires in 1 hour
            url = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': BUCKET_NAME, 'Key': filename},
                ExpiresIn=3600
            )

            return {"audioUrl": url}

        except ClientError as e:
            print(f"Error uploading to S3: {e}")
            raise HTTPException(status_code=500, detail="Failed to store audio file")

    except Exception as e:
        print(f"Error in text-to-speech: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
