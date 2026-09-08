from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import datetime

app = FastAPI(title="SIH26047 Pre-OPD Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

RED_FLAGS = [
    "chest pain", "heart attack", "bleeding", "unconscious", 
    "stroke", "paralysis", "chaati me dard", "chakkar", "severe breathlessness"
]

class IntakeSession(BaseModel):
    session_id: str
    patient_name: str
    age: int
    gender: str
    raw_transcript: str
    language: str = "hi"

class StructuredCaseSheet(BaseModel):
    session_id: str
    timestamp: str
    triage_status: str  # "EMERGENCY_RED" | "ROUTINE"
    chief_complaint: str
    duration: str
    socrates: dict
    ayush_indicators: dict
    fhir_bundle: dict

@app.post("/api/process-intake", response_model=StructuredCaseSheet)
def process_intake(session: IntakeSession):
    transcript = session.raw_transcript.lower()
    
    # 1. Deterministic Triage Rule (Instant Safety Check)
    is_emergency = any(word in transcript for word in RED_FLAGS)
    triage = "EMERGENCY_RED" if is_emergency else "ROUTINE"

    # 2. Clinical Extraction Simulation (SOCRATES + AYUSH)
    # Note: Replace this dict parsing with your LLM JSON-mode API call if API keys are active
    case_summary = {
        "site": "Chest/Retrosternal" if "chaati" in transcript or "chest" in transcript else "Abdomen/General",
        "onset": "Acute (last 3-4 hours)" if "aaj" in transcript or "today" in transcript else "Chronic (2-3 days)",
        "character": "Pressure / Tightness",
        "radiation": "Left arm and neck" if "haath" in transcript or "arm" in transcript else "Localized",
        "associations": ["Diaphoresis (Sweating)", "Nausea"],
        "severity": "8/10" if is_emergency else "4/10"
    }
    
    ayush_profile = {
        "dominant_dosha_aggravation": "Vata-Pitta",
        "agni": "Mandagni (Diminished digestion / heavy stomach)",
        "koshtha": "Krura (Constipated / irregular elimination)",
        "ahara_vihara_trigger": "Excessive Teekshna (spicy) food & Anidra (lack of sleep)"
    }

    # 3. ABDM FHIR R4 Bundle Construction
    fhir_bundle = {
        "resourceType": "Bundle",
        "id": f"bundle-{session.session_id}",
        "type": "document",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "entry": [
            {
                "resource": {
                    "resourceType": "Patient",
                    "id": session.session_id,
                    "name": [{"text": session.patient_name}],
                    "gender": session.gender,
                    "birthDate": str(2026 - session.age)
                }
            },
            {
                "resource": {
                    "resourceType": "Condition",
                    "clinicalStatus": {"text": "active"},
                    "verificationStatus": {"text": "preliminary"},
                    "code": {
                        "coding": [{
                            "system": "http://snomed.info/sct",
                            "code": "29857009" if is_emergency else "21522000",
                            "display": "Chest Pain" if is_emergency else "Abdominal Pain"
                        }],
                        "text": session.raw_transcript
                    }
                }
            },
            {
                "resource": {
                    "resourceType": "Observation",
                    "code": {"text": "AYUSH Ashtavidha Pariksha Intake"},
                    "valueString": f"Agni: {ayush_profile['agni']} | Koshtha: {ayush_profile['koshtha']}"
                }
            }
        ]
    }

    return StructuredCaseSheet(
        session_id=session.session_id,
        timestamp=datetime.datetime.now().strftime("%H:%M:%S"),
        triage_status=triage,
        chief_complaint=session.raw_transcript,
        duration="3 Days",
        socrates=case_summary,
        ayush_indicators=ayush_profile,
        fhir_bundle=fhir_bundle
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
