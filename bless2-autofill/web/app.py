"""
BLESS2 Auto-Fill Web GUI
=========================
FastAPI-based web interface for the BLESS2 Auto-Fill system.
Access at http://localhost:8000
"""

import os
import sys
import json
import uuid
import asyncio
import shutil
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.pdf_parser import PDFParser
from src.field_mapper import FieldMapper
from src.orchestrator import BLESS2Orchestrator

# ==========================================
# App Configuration
# ==========================================

app = FastAPI(
    title="BLESS2 Auto-Fill System",
    description="Web GUI untuk parse PDF dan auto-fill borang BLESS2",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directories
UPLOAD_DIR = Path("./uploads")
OUTPUT_DIR = Path("./output")
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# Store active jobs and their status
jobs: Dict[str, Dict[str, Any]] = {}

# WebSocket connections for real-time updates
active_connections: Dict[str, WebSocket] = {}


# ==========================================
# Static Files (Frontend)
# ==========================================

# Serve static frontend files
STATIC_DIR = Path(os.path.dirname(os.path.abspath(__file__))) / "static"
STATIC_DIR.mkdir(exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ==========================================
# API Routes
# ==========================================

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main dashboard page."""
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return HTMLResponse(content=index_path.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>BLESS2 Auto-Fill</h1><p>Static files not found.</p>")


@app.post("/api/upload")
async def upload_pdfs(files: list[UploadFile] = File(...)):
    """
    Upload PDF files for processing.
    Returns a session_id to track this batch.
    """
    session_id = str(uuid.uuid4())[:8]
    session_dir = UPLOAD_DIR / session_id
    session_dir.mkdir(exist_ok=True)
    
    uploaded_files = []
    
    for file in files:
        if not file.filename.lower().endswith(".pdf"):
            continue
            
        file_path = session_dir / file.filename
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        uploaded_files.append({
            "filename": file.filename,
            "size": len(content),
            "path": str(file_path),
        })
    
    if not uploaded_files:
        raise HTTPException(status_code=400, detail="No valid PDF files uploaded")
    
    return {
        "session_id": session_id,
        "files": uploaded_files,
        "message": f"{len(uploaded_files)} PDF file(s) uploaded successfully"
    }


@app.post("/api/parse/{session_id}")
async def parse_pdfs(session_id: str):
    """
    Parse uploaded PDFs and extract data.
    Returns structured extracted data.
    """
    session_dir = UPLOAD_DIR / session_id
    
    if not session_dir.exists():
        raise HTTPException(status_code=404, detail="Session not found. Upload files first.")
    
    try:
        parser = PDFParser(ocr_enabled=False)
        extracted_data = parser.parse_directory(str(session_dir))
        summary = parser.get_summary()
        
        # Map fields
        mapper = FieldMapper()
        sections = mapper.map_data(extracted_data)
        mapped_summary = mapper.get_mapped_summary()
        export_data = mapper.export_to_dict()
        
        # Save results
        output_file = OUTPUT_DIR / f"{session_id}_extracted.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        return {
            "session_id": session_id,
            "status": "success",
            "extraction_summary": summary,
            "mapped_data": mapped_summary,
            "full_data": export_data,
            "confidence_score": extracted_data.confidence_score,
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Parse error: {str(e)}")


@app.post("/api/preview/{session_id}")
async def preview_mapping(session_id: str):
    """
    Preview what fields will be filled without running automation.
    """
    session_dir = UPLOAD_DIR / session_id
    
    if not session_dir.exists():
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        parser = PDFParser(ocr_enabled=False)
        extracted_data = parser.parse_directory(str(session_dir))
        
        mapper = FieldMapper()
        sections = mapper.map_data(extracted_data)
        
        preview = []
        for section in sections:
            section_data = {
                "name": section.name,
                "fields": []
            }
            for field in section.fields:
                section_data["fields"].append({
                    "field_name": field.field_name,
                    "field_id": field.field_id,
                    "field_type": field.field_type,
                    "value": field.value,
                    "required": field.required,
                    "has_value": bool(field.value),
                })
            preview.append(section_data)
        
        return {
            "session_id": session_id,
            "preview": preview,
            "confidence_score": extracted_data.confidence_score,
            "company_name": extracted_data.company.company_name,
            "registration_no": extracted_data.company.registration_number,
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Preview error: {str(e)}")


@app.post("/api/run/{session_id}")
async def run_automation(
    session_id: str,
    username: str = Form(...),
    password: str = Form(...),
    headless: bool = Form(default=True),
    auto_submit: bool = Form(default=False),
):
    """
    Run the full automation (parse + fill BLESS2 form).
    Returns job_id for tracking progress via WebSocket.
    """
    session_dir = UPLOAD_DIR / session_id
    
    if not session_dir.exists():
        raise HTTPException(status_code=404, detail="Session not found")
    
    job_id = str(uuid.uuid4())[:8]
    
    # Initialize job status
    jobs[job_id] = {
        "status": "queued",
        "session_id": session_id,
        "progress": 0,
        "steps": [],
        "started_at": datetime.now().isoformat(),
        "result": None,
    }
    
    # Run automation in background
    asyncio.create_task(_run_automation_task(
        job_id, session_id, str(session_dir), username, password, headless, auto_submit
    ))
    
    return {
        "job_id": job_id,
        "status": "queued",
        "message": "Automation started. Connect to WebSocket for real-time updates.",
        "websocket_url": f"/ws/{job_id}"
    }


@app.get("/api/job/{job_id}")
async def get_job_status(job_id: str):
    """Get the status of a running job."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs[job_id]


@app.get("/api/download/{session_id}")
async def download_results(session_id: str):
    """Download extracted data as JSON."""
    output_file = OUTPUT_DIR / f"{session_id}_extracted.json"
    
    if not output_file.exists():
        raise HTTPException(status_code=404, detail="Results not found. Run parse first.")
    
    return FileResponse(
        path=str(output_file),
        filename=f"bless2_data_{session_id}.json",
        media_type="application/json"
    )


@app.delete("/api/session/{session_id}")
async def cleanup_session(session_id: str):
    """Clean up uploaded files for a session."""
    session_dir = UPLOAD_DIR / session_id
    if session_dir.exists():
        shutil.rmtree(session_dir)
    
    output_file = OUTPUT_DIR / f"{session_id}_extracted.json"
    if output_file.exists():
        output_file.unlink()
    
    return {"message": "Session cleaned up"}


# ==========================================
# WebSocket for Real-Time Updates
# ==========================================

@app.websocket("/ws/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    """WebSocket endpoint for real-time automation progress updates."""
    await websocket.accept()
    active_connections[job_id] = websocket
    
    try:
        while True:
            # Keep connection alive, send updates when available
            if job_id in jobs:
                await websocket.send_json(jobs[job_id])
                
                # Close if job completed or failed
                if jobs[job_id]["status"] in ("completed", "error", "failed"):
                    await asyncio.sleep(1)
                    break
            
            await asyncio.sleep(0.5)
            
    except WebSocketDisconnect:
        pass
    finally:
        active_connections.pop(job_id, None)


# ==========================================
# Background Task
# ==========================================

async def _run_automation_task(
    job_id: str,
    session_id: str,
    pdf_path: str,
    username: str,
    password: str,
    headless: bool,
    auto_submit: bool,
):
    """Background task that runs the full automation workflow."""
    
    async def update_status(status: str, progress: int, step: str = ""):
        jobs[job_id]["status"] = status
        jobs[job_id]["progress"] = progress
        if step:
            jobs[job_id]["steps"].append({
                "step": step,
                "timestamp": datetime.now().isoformat(),
                "progress": progress,
            })
        
        # Push to WebSocket if connected
        if job_id in active_connections:
            try:
                await active_connections[job_id].send_json(jobs[job_id])
            except Exception:
                pass

    try:
        await update_status("running", 10, "Initializing...")
        
        # Step 1: Parse PDFs
        await update_status("running", 20, "Parsing PDF documents...")
        
        parser = PDFParser(ocr_enabled=False)
        extracted_data = parser.parse_directory(pdf_path)
        parse_summary = parser.get_summary()
        
        await update_status("running", 40, f"PDF parsed. Company: {parse_summary['company_name']}")
        
        # Step 2: Map fields
        await update_status("running", 50, "Mapping fields to BLESS2 form...")
        
        mapper = FieldMapper()
        sections = mapper.map_data(extracted_data)
        
        total_fields = sum(len(s.fields) for s in sections)
        filled_fields = sum(1 for s in sections for f in s.fields if f.value)
        
        await update_status("running", 60, f"Mapped {filled_fields}/{total_fields} fields")
        
        # Step 3: Browser automation
        await update_status("running", 65, "Starting browser...")
        
        from src.browser_automation import BLESS2AutoFill, BrowserConfig
        
        config = BrowserConfig(headless=headless, slow_mode=True)
        automation = BLESS2AutoFill(config=config)
        
        try:
            automation.start_browser()
            await update_status("running", 70, "Browser started. Logging in...")
            
            login_success = automation.login(username, password)
            
            if not login_success:
                await update_status("failed", 70, "Login failed. Check credentials.")
                jobs[job_id]["result"] = {"error": "Login failed"}
                return
            
            await update_status("running", 80, "Login successful. Filling form...")
            
            automation.navigate_to_application("new")
            fill_results = automation.fill_form(sections, auto_submit=auto_submit)
            
            await update_status("completed", 100, 
                f"Done! {fill_results['filled_successfully']}/{fill_results['total_fields']} fields filled")
            
            jobs[job_id]["result"] = fill_results
            
        except Exception as e:
            await update_status("error", jobs[job_id]["progress"], f"Automation error: {str(e)}")
            jobs[job_id]["result"] = {"error": str(e)}
        finally:
            automation.close()
            
    except Exception as e:
        await update_status("error", 0, f"System error: {str(e)}")
        jobs[job_id]["result"] = {"error": str(e)}


# ==========================================
# Health Check
# ==========================================

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "BLESS2 Auto-Fill GUI",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
    }
