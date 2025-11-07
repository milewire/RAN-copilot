from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(Path(__file__).parent / ".env")

# Add engine and ai to path
# Handle both local development and Railway deployment
backend_dir = Path(__file__).parent

# Try local paths first (for Railway - engine/ai copied to backend/)
engine_path = backend_dir / "engine"
ai_path = backend_dir / "ai"

# If not found, try parent directory (for local development)
if not engine_path.exists():
    engine_path = backend_dir.parent / "engine"
if not ai_path.exists():
    ai_path = backend_dir.parent / "ai"

if engine_path.exists():
    sys.path.insert(0, str(engine_path))
if ai_path.exists():
    sys.path.insert(0, str(ai_path))

from parser import parse_ericsson_pm_xml
from rca import analyze_rca
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import gzip
import zipfile
import tempfile
import shutil
import time
from datetime import datetime, timedelta
import pandas as pd

# AI module imports
from gpt_summary import generate_ai_summary
from anomaly_detector import detect_anomalies, prepare_hourly_data
from drift_detector import detect_drift
from nlq import answer_question

app = FastAPI(title="LTE Band 41 RCA API", version="1.0.0")

# CORS configuration
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Temporary storage for uploaded files
UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# File retention settings (in hours)
FILE_RETENTION_HOURS = 24  # Files older than 24 hours will be deleted


class RCAResponse(BaseModel):
    root_cause: str
    severity: str
    evidence: Dict[str, Any]
    anomalies: List[Dict[str, Any]]
    recommendations: List[str]
    kpi_data: List[Dict[str, Any]]
    # AI-enhanced fields
    ai_summary: Optional[str] = None
    anomaly_detection: Optional[Dict[str, Any]] = None
    drift: Optional[Dict[str, Any]] = None


class AskAIRequest(BaseModel):
    question: str
    site: Optional[str] = None
    time_range: Optional[str] = None


class AskAIResponse(BaseModel):
    answer: str
    confidence: float


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "LTE Band 41 RCA API"}


def cleanup_old_files():
    """Remove files older than FILE_RETENTION_HOURS from uploads directory"""
    if not UPLOAD_DIR.exists():
        return
    
    cutoff_time = time.time() - (FILE_RETENTION_HOURS * 3600)
    deleted_count = 0
    
    for file_path in UPLOAD_DIR.iterdir():
        if file_path.is_file():
            try:
                if file_path.stat().st_mtime < cutoff_time:
                    file_path.unlink()
                    deleted_count += 1
            except Exception as e:
                print(f"Error deleting file {file_path}: {e}")
    
    if deleted_count > 0:
        print(f"Cleaned up {deleted_count} old file(s) from uploads directory")


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload and store PM XML file temporarily"""
    if not file.filename.endswith(('.xml.gz', '.gz', '.zip', '.xml')):
        raise HTTPException(status_code=400, detail="File must be .xml.gz, .gz, .zip, or .xml format")
    
    # Clean up old files before uploading new one
    cleanup_old_files()
    
    # Save file temporarily
    file_path = UPLOAD_DIR / file.filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    return {
        "filename": file.filename,
        "path": str(file_path),
        "message": f"File uploaded successfully. Files are retained for {FILE_RETENTION_HOURS} hours."
    }


@app.post("/analyze", response_model=RCAResponse)
async def analyze_pm_file(file: UploadFile = File(...)):
    """Parse PM XML file and run RCA analysis with AI enhancements"""
    try:
        # Determine file type
        file_ext = file.filename.lower()
        is_zip = file_ext.endswith('.zip')
        is_gz = file_ext.endswith('.gz') or file_ext.endswith('.xml.gz')
        
        # Create temporary file with appropriate suffix
        suffix = ".zip" if is_zip else ".xml.gz"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            shutil.copyfileobj(file.file, tmp_file)
            tmp_path = tmp_file.name
        
        try:
            # Extract and read XML content based on file type
            xml_content = None
            
            if is_zip:
                # Handle ZIP file
                with zipfile.ZipFile(tmp_path, 'r') as zip_file:
                    # Look for XML files in the zip
                    xml_files = [f for f in zip_file.namelist() if f.endswith('.xml')]
                    if not xml_files:
                        raise HTTPException(
                            status_code=400, 
                            detail="ZIP file does not contain any XML files"
                        )
                    # Use the first XML file found
                    xml_content = zip_file.read(xml_files[0])
            elif is_gz:
                # Handle GZIP file
                try:
                    with gzip.open(tmp_path, 'rb') as gz_file:
                        xml_content = gz_file.read()
                except (gzip.BadGzipFile, OSError):
                    # If gzip fails, try reading as plain XML
                    with open(tmp_path, 'rb') as xml_file:
                        xml_content = xml_file.read()
            elif file_ext.endswith('.xml'):
                # Handle plain XML file
                with open(tmp_path, 'rb') as xml_file:
                    xml_content = xml_file.read()
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Unsupported file format. Please use .xml.gz, .gz, .zip, or .xml"
                )
            
            # Parse XML
            try:
                kpi_data = parse_ericsson_pm_xml(xml_content)
            except Exception as parse_error:
                # Provide more helpful error message
                error_msg = f"XML parsing failed: {str(parse_error)}. "
                error_msg += "The XML structure may not match expected Ericsson ENM PM format. "
                error_msg += "Please verify the file format."
                raise HTTPException(status_code=400, detail=error_msg)
            
            if not kpi_data:
                raise HTTPException(
                    status_code=400, 
                    detail="No KPI data found in XML file. The XML structure may not match the expected format. "
                           "Please check that the file contains PM measurement data in Ericsson ENM format."
                )
            
            # Run deterministic RCA analysis
            rca_result = analyze_rca(kpi_data)
            
            # AI Feature B: Anomaly Detection
            anomaly_result = {}
            try:
                kpi_df = prepare_hourly_data(kpi_data)
                if not kpi_df.empty:
                    anomaly_result = detect_anomalies(kpi_df)
            except Exception as e:
                # Continue if anomaly detection fails
                print(f"Anomaly detection error: {e}")
                anomaly_result = {"error": str(e)}
            
            # AI Feature C: Drift Detection
            drift_result = {}
            try:
                # Extract site ID from KPI data
                site_id = None
                if kpi_data:
                    site_id = kpi_data[0].get("site", "default")
                drift_result = detect_drift(kpi_data, site_id=site_id)
            except Exception as e:
                # Continue if drift detection fails
                print(f"Drift detection error: {e}")
                drift_result = {"error": str(e)}
            
            # AI Feature A: Generate AI Summary
            ai_summary_text = ""
            try:
                ai_summary_text = generate_ai_summary(
                    kpi_data,
                    rca_result,
                    anomaly_result,
                    drift_result,
                    use_local=True
                )
            except Exception as e:
                # Continue if AI summary fails
                print(f"AI summary error: {e}")
                ai_summary_text = "AI summary unavailable"
            
            return RCAResponse(
                root_cause=rca_result["root_cause"],
                severity=rca_result["severity"],
                evidence=rca_result["evidence"],
                anomalies=rca_result["anomalies"],
                recommendations=rca_result["recommendations"],
                kpi_data=kpi_data,
                ai_summary=ai_summary_text,
                anomaly_detection=anomaly_result,
                drift=drift_result
            )
        
        finally:
            # Clean up temporary file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    except gzip.BadGzipFile:
        raise HTTPException(status_code=400, detail="Invalid gzip file. The file may be corrupted or not a valid gzip archive.")
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Invalid ZIP file. The file may be corrupted or not a valid ZIP archive.")
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Analysis error: {error_trace}")  # Log full traceback for debugging
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


class AskAIRequestWithContext(BaseModel):
    question: str
    kpi_data: Optional[List[Dict[str, Any]]] = None
    rca_result: Optional[Dict[str, Any]] = None
    site: Optional[str] = None
    time_range: Optional[str] = None


@app.post("/ask-ai", response_model=AskAIResponse)
async def ask_ai_question(request: AskAIRequestWithContext):
    """AI Feature D: Answer natural language questions about KPI data"""
    try:
        # Use provided KPI context or empty list
        kpi_context = request.kpi_data or []
        rca_result = request.rca_result
        
        # Check if cloud/LLM is enabled
        allow_cloud = os.getenv("ALLOW_CLOUD", "0") == "1"
        api_key = os.getenv("OPENAI_API_KEY", "")
        use_local = not (allow_cloud and api_key)  # Use local if cloud not enabled OR no API key
        
        # Log for debugging
        print(f"[Ask AI] ALLOW_CLOUD={os.getenv('ALLOW_CLOUD', 'not set')}, "
              f"has_api_key={bool(api_key)}, use_local={use_local}")
        
        # Answer the question
        result = answer_question(
            request.question,
            kpi_context,
            rca_result,
            use_local=use_local
        )
        
        return AskAIResponse(
            answer=result["answer"],
            confidence=result["confidence"]
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI query failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

