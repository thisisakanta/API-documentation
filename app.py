from flask import Flask, request, jsonify
from flask_restx import Api, Resource, fields, reqparse
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
from datetime import datetime, timedelta
import uuid
from functools import wraps

app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = 'medscribe-secret-key'  # In production, use a secure environment variable
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)
jwt = JWTManager(app)
app.wsgi_app = ProxyFix(app.wsgi_app)

# Custom wrapper for jwt_required to make Swagger UI testing easier
def jwt_optional(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return jwt_required()(fn)(*args, **kwargs)
        except Exception:
            # For Swagger UI testing, proceed without valid token
            print("JWT validation failed, but proceeding for Swagger testing")
            return fn(*args, **kwargs)
    return wrapper

# Initialize Flask-RestX API
api = Api(
    app,
    version='1.0',
    title='MedScribe API',
    description='API for MedScribe - A digital prescription management system',
    doc='/api/docs',
    authorizations={
        'Bearer Auth': {
            'type': 'apiKey',
            'in': 'header',
            'name': 'Authorization',
            'description': 'Type "Bearer" followed by a space and the access token'
        }
    },
    security='Bearer Auth'
)

# Define namespaces for API resources
auth_ns = api.namespace('auth', description='Authentication operations')
doctor_ns = api.namespace('doctors', description='Doctor operations')
patient_ns = api.namespace('patients', description='Patient operations')
prescription_ns = api.namespace('prescriptions', description='Prescription operations')
medicine_ns = api.namespace('medicines', description='Medicine operations')

# Model definitions
user_model = api.model('User', {
    'id': fields.String(readonly=True, description='Unique identifier for the user', example='usr-123456789'),
    'email': fields.String(required=True, description='User email address', example='john.doe@example.com'),
    'name': fields.String(required=True, description='Full name of the user', example='John Doe'),
    'role': fields.String(required=True, description='User role: doctor or patient', example='doctor')
})

login_model = api.model('Login', {
    'email': fields.String(required=True, description='User email address', example='doctor@medscribe.com'),
    'password': fields.String(required=True, description='User password', example='password123')
})

register_model = api.model('Register', {
    'name': fields.String(required=True, description='Full name of the user', example='John Doe'),
    'email': fields.String(required=True, description='User email address', example='john.doe@example.com'),
    'password': fields.String(required=True, description='User password', example='password123'),
    'role': fields.String(required=True, description='User role: doctor or patient', example='doctor')
})

doctor_register_model = api.inherit('DoctorRegister', register_model, {
    'specialization': fields.String(required=True, description='Medical specialization', example='Cardiologist'),
    'phoneNumber': fields.String(required=True, description='Contact phone number', example='123-456-7890')
})

patient_register_model = api.inherit('PatientRegister', register_model, {
    'age': fields.Integer(required=True, description='Patient age', example=35),
    'gender': fields.String(required=True, description='Patient gender', example='male')
})

doctor_model = api.model('Doctor', {
    'id': fields.String(readonly=True, description='Unique identifier for the doctor', example='doc-123456789'),
    'name': fields.String(required=True, description='Full name of the doctor', example='Dr. Sarah Williams'),
    'email': fields.String(required=True, description='Doctor email address', example='sarah.williams@medscribe.com'),
    'specialization': fields.String(required=True, description='Medical specialization', example='Cardiologist'),
    'phoneNumber': fields.String(required=True, description='Contact phone number', example='123-456-7890')
})

patient_model = api.model('Patient', {
    'id': fields.String(readonly=True, description='Unique identifier for the patient', example='pat-123456789'),
    'name': fields.String(required=True, description='Full name of the patient', example='John Smith'),
    'email': fields.String(required=True, description='Patient email address', example='john.smith@example.com'),
    'age': fields.Integer(required=True, description='Patient age', example=45),
    'gender': fields.String(required=True, description='Patient gender', example='male')
})

medicine_model = api.model('Medicine', {
    'id': fields.String(readonly=True, description='Unique identifier for the medicine', example='med-123'),
    'name': fields.String(required=True, description='Medicine name', example='Lisinopril 10mg'),
    'dosage': fields.String(required=True, description='Dosage (e.g., "1", "2", "3", "sos")', example='1'),
    'timing': fields.String(required=True, description='When to take (e.g., "before_meal", "after_meal")', example='before_meal'),
    'instructions': fields.String(description='Special instructions', example='Take with water')
})

medicine_database_model = api.model('MedicineDatabaseEntry', {
    'id': fields.String(readonly=True, description='Unique identifier for the medicine', example='med-123'),
    'name': fields.String(required=True, description='Medicine name with strength', example='Lisinopril 10mg')
})

prescription_model = api.model('Prescription', {
    'id': fields.String(readonly=True, description='Unique identifier for the prescription', example='pres-123456'),
    'doctorId': fields.String(required=True, description='ID of the doctor who created the prescription', example='doc-123456'),
    'patientId': fields.String(required=True, description='ID of the patient for whom the prescription is written', example='pat-123456'),
    'date': fields.DateTime(required=True, description='Date the prescription was created', example='2023-04-18T10:30:00'),
    'diseaseDescription': fields.String(required=True, description='Disease or condition description', example='Hypertension'),
    'medicines': fields.List(fields.Nested(medicine_model), required=True, description='List of prescribed medicines'),
    'followUpDate': fields.DateTime(description='Recommended follow-up date', example='2023-05-18T10:30:00'),
    'advice': fields.String(description='Additional advice or notes', example='Reduce salt intake. Monitor blood pressure daily.'),
    'status': fields.String(description='Prescription status (active or completed)', example='active')
})

prescription_create_model = api.model('PrescriptionCreate', {
    'patientId': fields.String(required=True, description='ID of the patient for whom the prescription is written', example='pat-123456'),
    'diseaseDescription': fields.String(required=True, description='Disease or condition description', example='Hypertension'),
    'medicines': fields.List(fields.Nested(medicine_model), required=True, description='List of prescribed medicines'),
    'followUpDate': fields.DateTime(description='Recommended follow-up date', example='2023-05-18T10:30:00'),
    'advice': fields.String(description='Additional advice or notes', example='Reduce salt intake. Monitor blood pressure daily.')
})

prescription_summary_model = api.model('PrescriptionSummary', {
    'id': fields.String(readonly=True, description='Unique identifier for the prescription', example='pres-123456'),
    'doctor': fields.String(description='Name of the doctor who created the prescription', example='Dr. Sarah Williams'),
    'specialization': fields.String(description='Specialization of the doctor', example='Cardiologist'),
    'date': fields.DateTime(description='Date the prescription was created', example='2023-04-18T10:30:00'),
    'condition': fields.String(description='Disease or condition description', example='Hypertension'),
    'status': fields.String(description='Prescription status (active or completed)', example='active'),
    'medicines': fields.List(fields.String, description='List of medicine names', example=['Lisinopril 10mg', 'Hydrochlorothiazide 12.5mg'])
})

token_model = api.model('Token', {
    'access_token': fields.String(description='JWT access token', example='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'),
    'token_type': fields.String(description='Token type', example='Bearer'),
    'user': fields.Nested(user_model)
})

# Authentication endpoints
@auth_ns.route('/login')
class Login(Resource):
    @auth_ns.doc('user_login')
    @auth_ns.expect(login_model)
    @auth_ns.response(200, 'Success', token_model)
    @auth_ns.response(401, 'Authentication Failed')
    def post(self):
        """Log in a user and receive an access token"""
        data = request.json
        # This is where you would normally authenticate the user against a database
        # For this example, we'll simulate a successful authentication with mock data
        
        # For demo purposes, we're using hardcoded examples that match our examples in the models
        user_id = "usr-" + str(uuid.uuid4())[:8]
        
        # Create more realistic user data based on the email provided
        if 'doctor' in data['email']:
            user = {
                'id': user_id,
                'email': data['email'],
                'name': 'Dr. Sarah Williams',
                'role': 'doctor'
            }
        else:
            user = {
                'id': user_id,
                'email': data['email'],
                'name': 'John Smith',
                'role': 'patient'
            }
        
        access_token = create_access_token(identity=user_id)
        
        return {
            'access_token': access_token,
            'token_type': 'Bearer',
            'user': user
        }, 200

@auth_ns.route('/register/doctor')
class DoctorRegister(Resource):
    @auth_ns.doc('register_doctor')
    @auth_ns.expect(doctor_register_model)
    @auth_ns.response(201, 'Doctor registered successfully', token_model)
    @auth_ns.response(400, 'Invalid input')
    def post(self):
        """Register a new doctor"""
        data = request.json
        # Here you would normally save the user to a database
        
        # Generate a user_id and create a token
        user_id = str(uuid.uuid4())
        user = {
            'id': user_id,
            'email': data['email'],
            'name': data['name'],
            'role': 'doctor',
            'specialization': data['specialization'],
            'phoneNumber': data['phoneNumber']
        }
        
        access_token = create_access_token(identity=user_id)
        
        return {
            'access_token': access_token,
            'token_type': 'Bearer',
            'user': user
        }, 201

@auth_ns.route('/register/patient')
class PatientRegister(Resource):
    @auth_ns.doc('register_patient')
    @auth_ns.expect(patient_register_model)
    @auth_ns.response(201, 'Patient registered successfully', token_model)
    @auth_ns.response(400, 'Invalid input')
    def post(self):
        """Register a new patient"""
        data = request.json
        # Here you would normally save the user to a database
        
        # Generate a user_id and create a token
        user_id = str(uuid.uuid4())
        user = {
            'id': user_id,
            'email': data['email'],
            'name': data['name'],
            'role': 'patient',
            'age': data['age'],
            'gender': data['gender']
        }
        
        access_token = create_access_token(identity=user_id)
        
        return {
            'access_token': access_token,
            'token_type': 'Bearer',
            'user': user
        }, 201

# Doctor endpoints
@doctor_ns.route('/')
class DoctorList(Resource):
    @doctor_ns.doc('list_doctors')
    @doctor_ns.response(200, 'Success', [doctor_model])
    @jwt_optional
    def get(self):
        """Get a list of all doctors"""
        # In a real application, this would fetch from a database
        doctors = [
            {
                'id': 'doc-12345678',
                'name': 'Dr. Sarah Williams',
                'email': 'sarah.williams@medscribe.com',
                'specialization': 'Cardiologist',
                'phoneNumber': '123-456-7890'
            },
            {
                'id': 'doc-87654321',
                'name': 'Dr. Michael Chen',
                'email': 'michael.chen@medscribe.com',
                'specialization': 'General Practitioner',
                'phoneNumber': '987-654-3210'
            }
        ]
        return doctors, 200

@doctor_ns.route('/<string:id>')
@doctor_ns.param('id', 'The doctor identifier', example='doc-12345678')
class Doctor(Resource):
    @doctor_ns.doc('get_doctor')
    @doctor_ns.response(200, 'Success', doctor_model)
    @doctor_ns.response(404, 'Doctor not found')
    @jwt_optional
    def get(self, id):
        """Get doctor details by ID"""
        # In a real application, this would fetch from a database
        doctor = {
            'id': id,
            'name': 'Dr. Sarah Williams',
            'email': 'sarah.williams@medscribe.com',
            'specialization': 'Cardiologist',
            'phoneNumber': '123-456-7890'
        }
        return doctor, 200

@doctor_ns.route('/<string:id>/patients')
@doctor_ns.param('id', 'The doctor identifier')
class DoctorPatients(Resource):
    @doctor_ns.doc('get_doctor_patients')
    @doctor_ns.response(200, 'Success', [patient_model])
    @jwt_required()
    def get(self, id):
        """Get all patients of a specific doctor"""
        # In a real application, this would fetch from a database
        patients = [
            {
                'id': str(uuid.uuid4()),
                'name': 'John Smith',
                'email': 'john.smith@example.com',
                'age': 45,
                'gender': 'male'
            },
            {
                'id': str(uuid.uuid4()),
                'name': 'Emma Wilson',
                'email': 'emma.wilson@example.com',
                'age': 32,
                'gender': 'female'
            }
        ]
        return patients, 200

# Patient endpoints
@patient_ns.route('/')
class PatientList(Resource):
    @patient_ns.doc('list_patients')
    @patient_ns.response(200, 'Success', [patient_model])
    @jwt_optional
    def get(self):
        """Get a list of all patients"""
        # In a real application, this would fetch from a database
        patients = [
            {
                'id': 'pat-12345678',
                'name': 'John Smith',
                'email': 'john.smith@example.com',
                'age': 45,
                'gender': 'male'
            },
            {
                'id': 'pat-87654321',
                'name': 'Emma Wilson',
                'email': 'emma.wilson@example.com',
                'age': 32,
                'gender': 'female'
            }
        ]
        return patients, 200

@patient_ns.route('/<string:id>')
@patient_ns.param('id', 'The patient identifier', example='pat-12345678')
class Patient(Resource):
    @patient_ns.doc('get_patient')
    @patient_ns.response(200, 'Success', patient_model)
    @patient_ns.response(404, 'Patient not found')
    @jwt_optional
    def get(self, id):
        """Get patient details by ID"""
        # In a real application, this would fetch from a database
        patient = {
            'id': id,
            'name': 'John Smith',
            'email': 'john.smith@example.com',
            'age': 45,
            'gender': 'male'
        }
        return patient, 200

# Prescription endpoints
@prescription_ns.route('/')
class PrescriptionList(Resource):
    @prescription_ns.doc('list_prescriptions')
    @prescription_ns.response(200, 'Success', [prescription_summary_model])
    @jwt_optional
    def get(self):
        """Get a list of all prescriptions for the authenticated user (doctor or patient)"""
        # For Swagger testing, we'll use a mock user ID
        try:
            current_user_id = get_jwt_identity()
        except:
            current_user_id = "doc-12345678"

        # In a real app, you would determine the user's role and fetch appropriate prescriptions
        # For this example, we'll return mock data
        prescriptions = [
            {
                'id': 'pres-123456',
                'doctor': 'Dr. Sarah Williams',
                'specialization': 'Cardiologist',
                'date': datetime(2023, 4, 18),
                'condition': 'Hypertension',
                'status': 'active',
                'medicines': ['Lisinopril 10mg', 'Hydrochlorothiazide 12.5mg']
            },
            {
                'id': 'pres-789012',
                'doctor': 'Dr. Michael Chen',
                'specialization': 'General Practitioner',
                'date': datetime(2023, 3, 10),
                'condition': 'Upper Respiratory Infection',
                'status': 'completed',
                'medicines': ['Amoxicillin 500mg', 'Guaifenesin 400mg']
            }
        ]
        return prescriptions, 200
    
    @prescription_ns.doc('create_prescription')
    @prescription_ns.expect(prescription_create_model)
    @prescription_ns.response(201, 'Prescription created', prescription_model)
    @prescription_ns.response(400, 'Invalid input')
    @prescription_ns.response(403, 'Only doctors can create prescriptions')
    @jwt_optional
    def post(self):
        """Create a new prescription (doctor only)"""
        # For Swagger testing, we'll use a mock user ID
        try:
            current_user_id = get_jwt_identity()
        except:
            current_user_id = "doc-12345678"
        
        # In a real app, you would check if the current user is a doctor
        # Here we'll assume the check passes
        
        data = request.json
        
        # Create a new prescription object
        prescription = {
            'id': 'pres-' + str(uuid.uuid4())[:6],
            'doctorId': current_user_id,
            'patientId': data['patientId'],
            'date': datetime.now(),
            'diseaseDescription': data['diseaseDescription'],
            'medicines': data['medicines'],
            'followUpDate': data.get('followUpDate'),
            'advice': data.get('advice', ''),
            'status': 'active'
        }
        
        # In a real app, you would save this to a database
        
        return prescription, 201

@prescription_ns.route('/<string:id>')
@prescription_ns.param('id', 'The prescription identifier', example='pres-123456')
class Prescription(Resource):
    @prescription_ns.doc('get_prescription')
    @prescription_ns.response(200, 'Success', prescription_model)
    @prescription_ns.response(404, 'Prescription not found')
    @jwt_optional
    def get(self, id):
        """Get prescription details by ID"""
        # For Swagger testing, we'll use a mock user ID
        try:
            current_user_id = get_jwt_identity()
        except:
            current_user_id = "doc-12345678"
        
        # In a real app, you would check if the user has permission to view this prescription
        # and fetch from a database
        
        # Mock data
        prescription = {
            'id': id,
            'doctorId': 'doc-12345678',
            'patientId': 'pat-12345678',
            'date': datetime(2023, 4, 18),
            'diseaseDescription': 'Hypertension',
            'medicines': [
                {
                    'id': 'med-1',
                    'name': 'Lisinopril 10mg',
                    'dosage': '1',  # Once daily
                    'timing': 'morning',
                    'instructions': 'Take with or without food'
                },
                {
                    'id': 'med-2',
                    'name': 'Hydrochlorothiazide 12.5mg',
                    'dosage': '1',  # Once daily
                    'timing': 'morning',
                    'instructions': 'Take with food'
                }
            ],
            'followUpDate': datetime(2023, 5, 18),
            'advice': 'Reduce salt intake. Monitor blood pressure daily.',
            'status': 'active'
        }
        
        return prescription, 200
    
    @prescription_ns.doc('update_prescription')
    @prescription_ns.expect(prescription_model)
    @prescription_ns.response(200, 'Prescription updated', prescription_model)
    @prescription_ns.response(403, 'Only the prescribing doctor can update')
    @prescription_ns.response(404, 'Prescription not found')
    @jwt_optional
    def put(self, id):
        """Update a prescription (doctor only)"""
        # For Swagger testing, we'll use a mock user ID
        try:
            current_user_id = get_jwt_identity()
        except:
            current_user_id = "doc-12345678"
        
        # In a real app, you would check if the user is a doctor and created this prescription
        # and update it in the database
        
        data = request.json
        
        # Handle date parsing more flexibly for Swagger UI testing
        try:
            date = datetime.fromisoformat(data['date'])
        except (ValueError, TypeError):
            date = datetime.now()
            
        try:
            followup_date = datetime.fromisoformat(data['followUpDate']) if data.get('followUpDate') else None
        except (ValueError, TypeError):
            followup_date = datetime.now() + timedelta(days=30)
        
        prescription = {
            'id': id,
            'doctorId': current_user_id,
            'patientId': data.get('patientId', 'pat-12345678'),
            'date': date,
            'diseaseDescription': data.get('diseaseDescription', 'Hypertension'),
            'medicines': data.get('medicines', [
                {
                    'id': 'med-1',
                    'name': 'Lisinopril 10mg',
                    'dosage': '1',
                    'timing': 'morning',
                    'instructions': 'Take with or without food'
                }
            ]),
            'followUpDate': followup_date,
            'advice': data.get('advice', ''),
            'status': data.get('status', 'active')
        }
        
        return prescription, 200

@prescription_ns.route('/doctor/<string:doctor_id>')
@prescription_ns.param('doctor_id', 'The doctor identifier', example='doc-12345678')
class DoctorPrescriptions(Resource):
    @prescription_ns.doc('get_doctor_prescriptions')
    @prescription_ns.response(200, 'Success', [prescription_summary_model])
    @jwt_optional
    def get(self, doctor_id):
        """Get all prescriptions written by a specific doctor"""
        # For Swagger testing, we'll use a mock user ID
        try:
            current_user_id = get_jwt_identity()
        except:
            current_user_id = "doc-12345678"
        
        # In a real app, you would check permissions and fetch from a database
        
        # Mock data
        prescriptions = [
            {
                'id': 'pres-123456',
                'doctor': 'Dr. Sarah Williams',
                'specialization': 'Cardiologist',
                'date': datetime(2023, 4, 18),
                'condition': 'Hypertension',
                'status': 'active',
                'medicines': ['Lisinopril 10mg', 'Hydrochlorothiazide 12.5mg']
            },
            {
                'id': 'pres-456789',
                'doctor': 'Dr. Sarah Williams',
                'specialization': 'Cardiologist',
                'date': datetime(2023, 3, 15),
                'condition': 'Cardiac Arrhythmia',
                'status': 'active',
                'medicines': ['Metoprolol 25mg']
            }
        ]
        
        return prescriptions, 200

@prescription_ns.route('/patient/<string:patient_id>')
@prescription_ns.param('patient_id', 'The patient identifier', example='pat-12345678')
class PatientPrescriptions(Resource):
    @prescription_ns.doc('get_patient_prescriptions')
    @prescription_ns.response(200, 'Success', [prescription_summary_model])
    @jwt_optional
    def get(self, patient_id):
        """Get all prescriptions for a specific patient"""
        # For Swagger testing, we'll use a mock user ID
        try:
            current_user_id = get_jwt_identity()
        except:
            current_user_id = "doc-12345678"
        
        # In a real app, you would check permissions and fetch from a database
        
        # Mock data
        prescriptions = [
            {
                'id': 'pres-123456',
                'doctor': 'Dr. Sarah Williams',
                'specialization': 'Cardiologist',
                'date': datetime(2023, 4, 18),
                'condition': 'Hypertension',
                'status': 'active',
                'medicines': ['Lisinopril 10mg', 'Hydrochlorothiazide 12.5mg']
            },
            {
                'id': 'pres-789012',
                'doctor': 'Dr. Michael Chen',
                'specialization': 'General Practitioner',
                'date': datetime(2023, 3, 10),
                'condition': 'Upper Respiratory Infection',
                'status': 'completed',
                'medicines': ['Amoxicillin 500mg', 'Guaifenesin 400mg']
            }
        ]
        
        return prescriptions, 200

# Medicine database endpoints
@medicine_ns.route('/')
class MedicineList(Resource):
    @medicine_ns.doc('list_medicines')
    @medicine_ns.response(200, 'Success', [medicine_database_model])
    @jwt_optional
    def get(self):
        """Get a list of all available medicines in the database"""
        # In a real application, this would fetch from a database
        medicines = [
            {"id": "med-1", "name": "Amoxicillin 250mg"},
            {"id": "med-2", "name": "Amoxicillin 500mg"},
            {"id": "med-3", "name": "Aspirin 81mg"},
            {"id": "med-4", "name": "Aspirin 325mg"},
            {"id": "med-5", "name": "Atorvastatin 10mg"},
            {"id": "med-6", "name": "Atorvastatin 20mg"},
            {"id": "med-7", "name": "Atorvastatin 40mg"},
            {"id": "med-8", "name": "Atorvastatin 80mg"},
            {"id": "med-9", "name": "Lisinopril 5mg"},
            {"id": "med-10", "name": "Lisinopril 10mg"},
            {"id": "med-11", "name": "Lisinopril 20mg"},
            {"id": "med-12", "name": "Metformin 500mg"},
            {"id": "med-13", "name": "Metformin 850mg"},
            {"id": "med-14", "name": "Metformin 1000mg"}
        ]
        return medicines, 200

@medicine_ns.route('/search')
class MedicineSearch(Resource):
    @medicine_ns.doc('search_medicines')
    @medicine_ns.param('query', 'Search query string', example='lisin')
    @medicine_ns.response(200, 'Success', [medicine_database_model])
    @jwt_optional
    def get(self):
        """Search for medicines by name"""
        query = request.args.get('query', '')
        
        # In a real application, this would fetch from a database based on the search query
        all_medicines = [
            {"id": "med-1", "name": "Amoxicillin 250mg"},
            {"id": "med-2", "name": "Amoxicillin 500mg"},
            {"id": "med-3", "name": "Aspirin 81mg"},
            {"id": "med-4", "name": "Aspirin 325mg"},
            {"id": "med-5", "name": "Atorvastatin 10mg"},
            {"id": "med-6", "name": "Atorvastatin 20mg"},
            {"id": "med-7", "name": "Atorvastatin 40mg"},
            {"id": "med-8", "name": "Atorvastatin 80mg"},
            {"id": "med-9", "name": "Lisinopril 5mg"},
            {"id": "med-10", "name": "Lisinopril 10mg"},
            {"id": "med-11", "name": "Lisinopril 20mg"},
            {"id": "med-12", "name": "Metformin 500mg"},
            {"id": "med-13", "name": "Metformin 850mg"},
            {"id": "med-14", "name": "Metformin 1000mg"}
        ]
        
        # Filter medicines based on the query
        if query:
            filtered_medicines = [med for med in all_medicines if query.lower() in med["name"].lower()]
        else:
            filtered_medicines = all_medicines
        
        return filtered_medicines, 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)