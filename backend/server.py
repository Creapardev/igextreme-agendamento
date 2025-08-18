from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date, time, timedelta
import os
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import uuid
from dotenv import load_dotenv
import requests
import asyncio

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

# WhatsApp API configuration
WHATSAPP_API_URL = os.getenv("WHATSAPP_API_URL", "")
WHATSAPP_INSTANCE = os.getenv("WHATSAPP_INSTANCE", "")
WHATSAPP_API_KEY = os.getenv("WHATSAPP_API_KEY", "")

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

class ScheduleWeekCreate(BaseModel):
    start_date: str
    weeks: int = 4  # Quantas semanas criar

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

# WhatsApp notification functions
async def send_whatsapp_notification(phone_number: str, message: str):
    """Send WhatsApp notification via Evolution API"""
    if not WHATSAPP_API_URL or not WHATSAPP_API_KEY:
        print("WhatsApp API not configured")
        return False
    
    try:
        # Remove any formatting from phone number and ensure it has country code
        clean_phone = phone_number.replace("(", "").replace(")", "").replace("-", "").replace(" ", "")
        if not clean_phone.startswith("55"):
            clean_phone = "55" + clean_phone
        
        headers = {
            "Content-Type": "application/json",
            "apikey": WHATSAPP_API_KEY
        }
        
        payload = {
            "number": clean_phone,
            "text": message
        }
        
        print(f"Sending WhatsApp to {clean_phone}: {message[:50]}...")
        
        response = requests.post(WHATSAPP_API_URL, json=payload, headers=headers)
        
        if response.status_code == 200 or response.status_code == 201:
            print("✅ WhatsApp notification sent successfully")
            return True
        else:
            print(f"❌ WhatsApp API error: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error sending WhatsApp notification: {str(e)}")
        return False

def generate_time_slots():
    """Generate time slots for scheduling"""
    slots = []
    
    # Segunda a Sexta: 08:00-12:00 e 16:00-20:00
    weekday_morning = []
    for hour in range(8, 12):  # 8:00 to 11:30
        for minute in [0, 30]:
            weekday_morning.append(f"{hour:02d}:{minute:02d}:00")
    
    weekday_afternoon = []
    for hour in range(16, 20):  # 16:00 to 19:30
        for minute in [0, 30]:
            weekday_afternoon.append(f"{hour:02d}:{minute:02d}:00")
    
    # Sábado: 09:00-12:00
    saturday_slots = []
    for hour in range(9, 12):  # 9:00 to 11:30
        for minute in [0, 30]:
            saturday_slots.append(f"{hour:02d}:{minute:02d}:00")
    
    return {
        "weekday_morning": weekday_morning,
        "weekday_afternoon": weekday_afternoon,
        "saturday": saturday_slots
    }

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
            
            # Send WhatsApp notifications
            client_message = f"""✅ *AGENDAMENTO CONFIRMADO*

Olá *{appointment.client_name}*! 👋

Seu agendamento foi confirmado com sucesso:

📅 *Data:* {datetime.strptime(appointment.date, '%Y-%m-%d').strftime('%d/%m/%Y')}
🕐 *Horário:* {appointment.time[:5]}
⏱️ *Duração:* 30 minutos

📍 *Creapar*
_Sistema de Agendamento_

Em caso de dúvidas, entre em contato conosco!"""
            
            admin_message = f"""🔔 *NOVO AGENDAMENTO*

👤 *Cliente:* {appointment.client_name}
📱 *WhatsApp:* {appointment.whatsapp}
📅 *Data:* {datetime.strptime(appointment.date, '%Y-%m-%d').strftime('%d/%m/%Y')}
🕐 *Horário:* {appointment.time[:5]}
📝 *Observações:* {appointment.notes or 'Nenhuma'}

_Creapar - Sistema de Agendamento_"""
            
            # Send notifications (async)
            asyncio.create_task(send_whatsapp_notification(appointment.whatsapp, client_message))
            # Para admin, você precisará configurar o número do admin
            
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

@app.post("/api/schedule/bulk-create")
async def create_schedule_bulk(schedule: ScheduleWeekCreate):
    """Create schedule for multiple weeks with default business hours"""
    try:
        start_dt = datetime.strptime(schedule.start_date, "%Y-%m-%d")
        slots_created = 0
        time_slots = generate_time_slots()
        
        for week in range(schedule.weeks):
            for day in range(7):  # 0=Monday, 6=Sunday
                current_date = start_dt + timedelta(weeks=week, days=day)
                date_str = current_date.strftime("%Y-%m-%d")
                weekday = current_date.weekday()
                
                # Skip Sundays (weekday 6)
                if weekday == 6:
                    continue
                
                # Determine which time slots to use
                slots_for_day = []
                if weekday < 5:  # Monday to Friday (0-4)
                    slots_for_day.extend(time_slots["weekday_morning"])
                    slots_for_day.extend(time_slots["weekday_afternoon"])
                elif weekday == 5:  # Saturday (5)
                    slots_for_day.extend(time_slots["saturday"])
                
                # Create slots for this day
                for time_slot in slots_for_day:
                    # Check if slot already exists
                    existing_slot = await available_slots_collection.find_one({
                        "date": date_str,
                        "time": time_slot
                    })
                    
                    if not existing_slot:
                        slot_dict = AvailableSlot(
                            date=date_str,
                            time=time_slot,
                            type="appointment"
                        ).dict()
                        
                        await available_slots_collection.insert_one(slot_dict)
                        slots_created += 1
        
        return {
            "message": f"Criados {slots_created} horários para {schedule.weeks} semanas",
            "slots_created": slots_created,
            "start_date": schedule.start_date,
            "weeks": schedule.weeks
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating bulk schedule: {str(e)}")

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