import requests
import sys
import json
from datetime import datetime, date, timedelta
import uuid

class CreaparAPITester:
    def __init__(self, base_url="https://appointment-hub-44.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.created_slots = []
        self.created_appointments = []

    def run_test(self, name, method, endpoint, expected_status, data=None, params=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    if isinstance(response_data, list) and len(response_data) > 0:
                        print(f"   Response: {len(response_data)} items returned")
                    elif isinstance(response_data, dict):
                        print(f"   Response keys: {list(response_data.keys())}")
                except:
                    print(f"   Response: {response.text[:100]}...")
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text}")

            return success, response.json() if response.text else {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_health_check(self):
        """Test health check endpoint"""
        success, response = self.run_test(
            "Health Check",
            "GET",
            "api/health",
            200
        )
        return success

    def test_get_available_slots_all(self):
        """Test getting all available slots"""
        success, response = self.run_test(
            "Get All Available Slots",
            "GET",
            "api/available-slots",
            200
        )
        return success, response

    def test_get_available_slots_by_date(self, test_date):
        """Test getting available slots for specific date"""
        success, response = self.run_test(
            f"Get Available Slots for {test_date}",
            "GET",
            "api/available-slots",
            200,
            params={"date": test_date}
        )
        return success, response

    def test_create_available_slot(self, test_date, test_time):
        """Test creating a new available slot"""
        slot_data = {
            "date": test_date,
            "time": test_time,
            "type": "appointment"
        }
        
        success, response = self.run_test(
            f"Create Available Slot ({test_date} {test_time})",
            "POST",
            "api/available-slots",
            201,
            data=slot_data
        )
        
        if success and 'id' in response:
            self.created_slots.append(response)
            return True, response
        return False, {}

    def test_create_duplicate_slot(self, test_date, test_time):
        """Test creating duplicate slot (should fail)"""
        slot_data = {
            "date": test_date,
            "time": test_time,
            "type": "appointment"
        }
        
        success, response = self.run_test(
            f"Create Duplicate Slot (should fail)",
            "POST",
            "api/available-slots",
            400,  # Should fail with 400
            data=slot_data
        )
        return success

    def test_get_appointments_all(self):
        """Test getting all appointments"""
        success, response = self.run_test(
            "Get All Appointments",
            "GET",
            "api/appointments",
            200
        )
        return success, response

    def test_get_appointments_by_date(self, test_date):
        """Test getting appointments for specific date"""
        success, response = self.run_test(
            f"Get Appointments for {test_date}",
            "GET",
            "api/appointments",
            200,
            params={"date": test_date}
        )
        return success, response

    def test_create_appointment(self, slot_id, test_date, test_time):
        """Test creating a new appointment"""
        appointment_data = {
            "slot_id": slot_id,
            "client_name": "Test Client",
            "whatsapp": "(11) 99999-9999",
            "notes": "Test appointment notes",
            "date": test_date,
            "time": test_time
        }
        
        success, response = self.run_test(
            f"Create Appointment for slot {slot_id}",
            "POST",
            "api/appointments",
            201,
            data=appointment_data
        )
        
        if success and 'id' in response:
            self.created_appointments.append(response)
            return True, response
        return False, {}

    def test_create_appointment_unavailable_slot(self, slot_id, test_date, test_time):
        """Test creating appointment for unavailable slot (should fail)"""
        appointment_data = {
            "slot_id": slot_id,
            "client_name": "Test Client 2",
            "whatsapp": "(11) 88888-8888",
            "notes": "Should fail",
            "date": test_date,
            "time": test_time
        }
        
        success, response = self.run_test(
            f"Create Appointment for unavailable slot (should fail)",
            "POST",
            "api/appointments",
            400,  # Should fail with 400
            data=appointment_data
        )
        return success

    def test_get_appointment_by_id(self, appointment_id):
        """Test getting specific appointment by ID"""
        success, response = self.run_test(
            f"Get Appointment by ID {appointment_id}",
            "GET",
            f"api/appointments/{appointment_id}",
            200
        )
        return success, response

    def test_cancel_appointment(self, appointment_id):
        """Test cancelling an appointment"""
        success, response = self.run_test(
            f"Cancel Appointment {appointment_id}",
            "PUT",
            f"api/appointments/{appointment_id}/cancel",
            200
        )
        return success, response

    def test_delete_available_slot(self, slot_id):
        """Test deleting an available slot"""
        success, response = self.run_test(
            f"Delete Available Slot {slot_id}",
            "DELETE",
            f"api/available-slots/{slot_id}",
            200
        )
        return success, response

def main():
    print("🚀 Starting Creapar API Tests...")
    print("=" * 50)
    
    tester = CreaparAPITester()
    
    # Test dates - tomorrow and day after tomorrow
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    day_after = (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d')
    test_time_1 = "09:00:00"
    test_time_2 = "10:30:00"
    
    print(f"Using test dates: {tomorrow}, {day_after}")
    print(f"Using test times: {test_time_1}, {test_time_2}")
    
    # 1. Basic connectivity tests
    print("\n" + "="*50)
    print("1. BASIC CONNECTIVITY TESTS")
    print("="*50)
    
    if not tester.test_health_check():
        print("❌ Health check failed - stopping tests")
        return 1
    
    # 2. Available slots tests
    print("\n" + "="*50)
    print("2. AVAILABLE SLOTS TESTS")
    print("="*50)
    
    # Get initial slots
    success, initial_slots = tester.test_get_available_slots_all()
    if not success:
        print("❌ Failed to get initial slots")
        return 1
    
    # Get slots by date (should be empty initially)
    tester.test_get_available_slots_by_date(tomorrow)
    
    # Create new available slots
    success1, slot1 = tester.test_create_available_slot(tomorrow, test_time_1)
    success2, slot2 = tester.test_create_available_slot(day_after, test_time_2)
    
    if not (success1 and success2):
        print("❌ Failed to create test slots")
        return 1
    
    # Test duplicate slot creation (should fail)
    tester.test_create_duplicate_slot(tomorrow, test_time_1)
    
    # Verify slots were created
    success, slots_after_creation = tester.test_get_available_slots_by_date(tomorrow)
    if success and len(slots_after_creation) > 0:
        print(f"✅ Successfully created and retrieved slots for {tomorrow}")
    
    # 3. Appointments tests
    print("\n" + "="*50)
    print("3. APPOINTMENTS TESTS")
    print("="*50)
    
    # Get initial appointments
    success, initial_appointments = tester.test_get_appointments_all()
    if not success:
        print("❌ Failed to get initial appointments")
        return 1
    
    # Create appointment for first slot
    success, appointment1 = tester.test_create_appointment(
        slot1['id'], tomorrow, test_time_1
    )
    
    if not success:
        print("❌ Failed to create test appointment")
        return 1
    
    # Try to create another appointment for same slot (should fail)
    tester.test_create_appointment_unavailable_slot(
        slot1['id'], tomorrow, test_time_1
    )
    
    # Get appointment by ID
    tester.test_get_appointment_by_id(appointment1['id'])
    
    # Get appointments by date
    success, appointments_by_date = tester.test_get_appointments_by_date(tomorrow)
    if success and len(appointments_by_date) > 0:
        print(f"✅ Successfully retrieved appointments for {tomorrow}")
    
    # 4. Cancellation and cleanup tests
    print("\n" + "="*50)
    print("4. CANCELLATION AND CLEANUP TESTS")
    print("="*50)
    
    # Cancel the appointment
    tester.test_cancel_appointment(appointment1['id'])
    
    # Verify slot is available again by checking available slots
    success, available_after_cancel = tester.test_get_available_slots_by_date(tomorrow)
    if success:
        available_slot_ids = [slot['id'] for slot in available_after_cancel if slot.get('is_available', False)]
        if slot1['id'] in available_slot_ids:
            print("✅ Slot became available again after cancellation")
        else:
            print("❌ Slot did not become available after cancellation")
    
    # Clean up - delete created slots
    for slot in tester.created_slots:
        tester.test_delete_available_slot(slot['id'])
    
    # Final results
    print("\n" + "="*50)
    print("FINAL RESULTS")
    print("="*50)
    print(f"📊 Tests passed: {tester.tests_passed}/{tester.tests_run}")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All tests passed!")
        return 0
    else:
        print(f"❌ {tester.tests_run - tester.tests_passed} tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())