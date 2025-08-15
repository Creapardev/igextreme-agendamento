from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date, time
import os
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import uuid
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Creapar Scheduling API", version="1.0.0")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB configuration
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
client = AsyncIOMotorClient(MONGO_URL)
db = client.creapar_scheduling

# Collections
available_slots_collection = db.available_slots
appointments_collection = db.appointments

# Pydantic models
class AvailableSlot(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    date: str
    time: str
    type: str = "appointment"  # appointment or event
    is_available: bool = True
    created_at: datetime = Field(default_factory=datetime.now)

class AvailableSlotCreate(BaseModel):
    date: str
    time: str
    type: str = "appointment"

class Appointment(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    slot_id: str
    client_name: str
    whatsapp: str
    notes: Optional[str] = None
    date: str
    time: str
    status: str = "confirmed"  # confirmed, cancelled, completed
    created_at: datetime = Field(default_factory=datetime.now)

class AppointmentCreate(BaseModel):
    slot_id: str
    client_name: str
    whatsapp: str
    notes: Optional[str] = None
    date: str
    time: str

# Helper functions
def serialize_doc(doc):
    """Convert MongoDB document to dict with string IDs"""
    if doc is None:
        return None
    doc['_id'] = str(doc['_id'])
    return doc

def serialize_docs(docs):
    """Convert list of MongoDB documents to list of dicts with string IDs"""
    return [serialize_doc(doc) for doc in docs]

# API Routes

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "Creapar Scheduling API is running"}

@app.get("/api/available-slots")
async def get_available_slots(date: Optional[str] = None):
    """Get available slots for a specific date or all dates"""
    try:
        query = {"is_available": True}
        if date:
            query["date"] = date
        
        cursor = available_slots_collection.find(query).sort("time", 1)
        slots = await cursor.to_list(length=100)
        
        return serialize_docs(slots)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching available slots: {str(e)}")

@app.post("/api/available-slots")
async def create_available_slot(slot: AvailableSlotCreate):
    """Create a new available slot"""
    try:
        # Check if slot already exists
        existing_slot = await available_slots_collection.find_one({
            "date": slot.date,
            "time": slot.time
        })
        
        if existing_slot:
            raise HTTPException(status_code=400, detail="Slot already exists for this date and time")
        
        slot_dict = AvailableSlot(**slot.dict()).dict()
        result = await available_slots_collection.insert_one(slot_dict)
        
        if result.inserted_id:
            created_slot = await available_slots_collection.find_one({"_id": result.inserted_id})
            return serialize_doc(created_slot)
        else:
            raise HTTPException(status_code=500, detail="Failed to create slot")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating available slot: {str(e)}")

@app.get("/api/appointments")
async def get_appointments(date: Optional[str] = None):
    """Get appointments for a specific date or all dates"""
    try:
        query = {}
        if date:
            query["date"] = date
        
        cursor = appointments_collection.find(query).sort("time", 1)
        appointments = await cursor.to_list(length=100)
        
        return serialize_docs(appointments)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching appointments: {str(e)}")

@app.post("/api/appointments")
async def create_appointment(appointment: AppointmentCreate):
    """Create a new appointment"""
    try:
        # Check if the slot exists and is available
        slot = await available_slots_collection.find_one({
            "id": appointment.slot_id,
            "is_available": True
        })
        
        if not slot:
            raise HTTPException(status_code=400, detail="Selected slot is not available")
        
        # Check if there's already an appointment for this slot
        existing_appointment = await appointments_collection.find_one({
            "slot_id": appointment.slot_id,
            "status": {"$ne": "cancelled"}
        })
        
        if existing_appointment:
            raise HTTPException(status_code=400, detail="This slot is already booked")
        
        # Create the appointment
        appointment_dict = Appointment(**appointment.dict()).dict()
        result = await appointments_collection.insert_one(appointment_dict)
        
        if result.inserted_id:
            # Mark the slot as unavailable
            await available_slots_collection.update_one(
                {"id": appointment.slot_id},
                {"$set": {"is_available": False}}
            )
            
            created_appointment = await appointments_collection.find_one({"_id": result.inserted_id})
            
            # Here you would send notifications (WhatsApp/Email)
            # TODO: Implement notification system
            print(f"New appointment created: {appointment.client_name} - {appointment.date} {appointment.time}")
            
            return serialize_doc(created_appointment)
        else:
            raise HTTPException(status_code=500, detail="Failed to create appointment")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating appointment: {str(e)}")

@app.get("/api/appointments/{appointment_id}")
async def get_appointment(appointment_id: str):
    """Get a specific appointment by ID"""
    try:
        appointment = await appointments_collection.find_one({"id": appointment_id})
        
        if not appointment:
            raise HTTPException(status_code=404, detail="Appointment not found")
        
        return serialize_doc(appointment)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching appointment: {str(e)}")

@app.put("/api/appointments/{appointment_id}/cancel")
async def cancel_appointment(appointment_id: str):
    """Cancel an appointment"""
    try:
        appointment = await appointments_collection.find_one({"id": appointment_id})
        
        if not appointment:
            raise HTTPException(status_code=404, detail="Appointment not found")
        
        # Update appointment status
        await appointments_collection.update_one(
            {"id": appointment_id},
            {"$set": {"status": "cancelled"}}
        )
        
        # Make the slot available again
        await available_slots_collection.update_one(
            {"id": appointment["slot_id"]},
            {"$set": {"is_available": True}}
        )
        
        return {"message": "Appointment cancelled successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error cancelling appointment: {str(e)}")

@app.delete("/api/available-slots/{slot_id}")
async def delete_available_slot(slot_id: str):
    """Delete an available slot"""
    try:
        # Check if there are any appointments for this slot
        appointment = await appointments_collection.find_one({
            "slot_id": slot_id,
            "status": {"$ne": "cancelled"}
        })
        
        if appointment:
            raise HTTPException(status_code=400, detail="Cannot delete slot with existing appointments")
        
        result = await available_slots_collection.delete_one({"id": slot_id})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Slot not found")
        
        return {"message": "Slot deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting slot: {str(e)}")

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize database indexes and collections"""
    try:
        # Create indexes for better performance
        await available_slots_collection.create_index([("date", 1), ("time", 1)])
        await available_slots_collection.create_index("id")
        await appointments_collection.create_index([("date", 1), ("time", 1)])
        await appointments_collection.create_index("id")
        await appointments_collection.create_index("slot_id")
        
        print("Database indexes created successfully")
    except Exception as e:
        print(f"Error creating database indexes: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)