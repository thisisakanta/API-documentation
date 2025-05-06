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
health_tip_ns = api.namespace('health-tips', description='Health tips operations')
notification_ns = api.namespace('notifications', description='Medication notification operations')
followup_ns = api.namespace('followups', description='Follow-up appointment operations')

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

doctor_update_model = api.model('DoctorUpdate', {
    'name': fields.String(description='Full name of the doctor', example='Dr. Sarah Williams'),
    'email': fields.String(description='Doctor email address', example='sarah.williams@medscribe.com'),
    'specialization': fields.String(description='Medical specialization', example='Cardiologist'),
    'phoneNumber': fields.String(description='Contact phone number', example='123-456-7890')
})

patient_model = api.model('Patient', {
    'id': fields.String(readonly=True, description='Unique identifier for the patient', example='pat-123456789'),
    'name': fields.String(required=True, description='Full name of the patient', example='John Smith'),
    'email': fields.String(required=True, description='Patient email address', example='john.smith@example.com'),
    'age': fields.Integer(required=True, description='Patient age', example=45),
    'gender': fields.String(required=True, description='Patient gender', example='male')
})

patient_update_model = api.model('PatientUpdate', {
    'name': fields.String(description='Full name of the patient', example='John Smith'),
    'email': fields.String(description='Patient email address', example='john.smith@example.com'),
    'age': fields.Integer(description='Patient age', example=45),
    'gender': fields.String(description='Patient gender', example='male')
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

health_tip_model = api.model('HealthTip', {
    'id': fields.String(readonly=True, description='Unique identifier for the health tip', example='tip-123456'),
    'title': fields.String(required=True, description='Title of the health tip', example='Managing Hypertension'),
    'content': fields.String(required=True, description='Content of the health tip', example='Regular exercise and reduced salt intake can help manage hypertension.'),
    'category': fields.String(required=True, description='Category of the health tip', example='cardiovascular'),
    'createdDate': fields.DateTime(readonly=True, description='Date the tip was created', example='2023-04-18T10:30:00'),
    'relevantConditions': fields.List(fields.String, description='List of conditions this tip is relevant for', example=['hypertension', 'heart disease'])
})

notification_model = api.model('Notification', {
    'id': fields.String(readonly=True, description='Unique identifier for the notification', example='notif-123456'),
    'patientId': fields.String(required=True, description='ID of the patient', example='pat-123456'),
    'prescriptionId': fields.String(required=True, description='ID of the prescription', example='pres-123456'),
    'medicineId': fields.String(required=True, description='ID of the medicine', example='med-1'),
    'medicineName': fields.String(readonly=True, description='Name of the medicine', example='Lisinopril 10mg'),
    'scheduledTime': fields.DateTime(required=True, description='Scheduled time for taking the medicine', example='2023-04-18T08:00:00'),
    'status': fields.String(description='Status of the notification (pending, taken, missed)', example='pending'),
    'isRead': fields.Boolean(description='Whether the notification has been read', example=False)
})

notification_update_model = api.model('NotificationUpdate', {
    'status': fields.String(required=True, description='New status (taken, missed)', example='taken'),
    'isRead': fields.Boolean(description='Whether to mark as read', example=True)
})

# Follow-up Models
followup_model = api.model('FollowUp', {
    'id': fields.String(readonly=True, description='Unique identifier for the follow-up', example='follow-123456'),
    'prescriptionId': fields.String(required=True, description='ID of the related prescription', example='pres-123456'),
    'doctorId': fields.String(required=True, description='ID of the doctor', example='doc-123456'),
    'patientId': fields.String(required=True, description='ID of the patient', example='pat-123456'),
    'scheduledDate': fields.DateTime(required=True, description='Scheduled date for the follow-up', example='2023-05-18T10:30:00'),
    'status': fields.String(description='Status of the follow-up (scheduled, completed, rescheduled, missed)', example='scheduled'),
    'notes': fields.String(description='Additional notes', example='Review blood pressure readings')
})

followup_update_model = api.model('FollowUpUpdate', {
    'status': fields.String(required=True, description='New status (completed, rescheduled, missed)', example='rescheduled'),
    'scheduledDate': fields.DateTime(description='New scheduled date if rescheduled', example='2023-05-25T10:30:00'),
    'notes': fields.String(description='Updated notes', example='Patient requested to reschedule')
})

# Extended Medicine Models
medicine_extended_model = api.model('MedicineExtended', {
    'id': fields.String(readonly=True, description='Unique identifier for the medicine', example='med-123'),
    'name': fields.String(required=True, description='Medicine name with strength', example='Lisinopril 10mg'),
    'group': fields.String(description='Therapeutic group/class', example='ACE Inhibitor'),
    'company': fields.String(description='Pharmaceutical company', example='AstraZeneca'),
    'description': fields.String(description='Description of the medicine', example='Used to treat high blood pressure and heart failure')
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
    
    @doctor_ns.doc('update_doctor')
    @doctor_ns.expect(doctor_update_model)
    @doctor_ns.response(200, 'Doctor updated', doctor_model)
    @doctor_ns.response(403, 'Unauthorized to update doctor')
    @doctor_ns.response(404, 'Doctor not found')
    @jwt_required()
    def put(self, id):
        """Update doctor details"""
        try:
            current_user_id = get_jwt_identity()
        except:
            return {'message': 'Authentication required'}, 401
        
        data = request.json
        
        # In a real app, verify user has permission to update this doctor
        # and update in the database
        
        doctor = {
            'id': id,
            'name': data.get('name', 'Dr. Sarah Williams'),
            'email': data.get('email', 'sarah.williams@medscribe.com'),
            'specialization': data.get('specialization', 'Cardiologist'),
            'phoneNumber': data.get('phoneNumber', '123-456-7890')
        }
        
        return doctor, 200
    
    @doctor_ns.doc('delete_doctor')
    @doctor_ns.response(204, 'Doctor deleted')
    @doctor_ns.response(403, 'Unauthorized to delete doctor')
    @doctor_ns.response(404, 'Doctor not found')
    @jwt_required()
    def delete(self, id):
        """Delete a doctor"""
        try:
            current_user_id = get_jwt_identity()
        except:
            return {'message': 'Authentication required'}, 401
        
        # In a real app, verify user has permission to delete this doctor
        # and delete from the database
        
        return '', 204

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
    
    @patient_ns.doc('update_patient')
    @patient_ns.expect(patient_update_model)
    @patient_ns.response(200, 'Patient updated', patient_model)
    @patient_ns.response(403, 'Unauthorized to update patient')
    @patient_ns.response(404, 'Patient not found')
    @jwt_required()
    def put(self, id):
        """Update patient details"""
        try:
            current_user_id = get_jwt_identity()
        except:
            return {'message': 'Authentication required'}, 401
        
        data = request.json
        
        # In a real app, verify user has permission to update this patient
        # and update in the database
        
        patient = {
            'id': id,
            'name': data.get('name', 'John Smith'),
            'email': data.get('email', 'john.smith@example.com'),
            'age': data.get('age', 45),
            'gender': data.get('gender', 'male')
        }
        
        return patient, 200
    
    @patient_ns.doc('delete_patient')
    @patient_ns.response(204, 'Patient deleted')
    @patient_ns.response(403, 'Unauthorized to delete patient')
    @patient_ns.response(404, 'Patient not found')
    @jwt_required()
    def delete(self, id):
        """Delete a patient"""
        try:
            current_user_id = get_jwt_identity()
        except:
            return {'message': 'Authentication required'}, 401
        
        # In a real app, verify user has permission to delete this patient
        # and delete from the database
        
        return '', 204

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
            {"id": "med- personally identifiable information redacted"},
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


@health_tip_ns.route('/')
class HealthTipList(Resource):
    @health_tip_ns.doc('list_health_tips')
    @health_tip_ns.response(200, 'Success', [health_tip_model])
    @jwt_optional
    def get(self):
        """Get a list of all health tips"""
        # In a real application, this would fetch from a database
        health_tips = [
            {
                'id': 'tip-123456',
                'title': 'Managing Hypertension',
                'content': 'Regular exercise and reduced salt intake can help manage hypertension. Aim for at least 30 minutes of moderate exercise most days of the week.',
                'category': 'cardiovascular',
                'createdDate': datetime(2023, 4, 15),
                'relevantConditions': ['hypertension', 'heart disease']
            },
            {
                'id': 'tip-234567',
                'title': 'Diabetic Diet Tips',
                'content': 'Include complex carbohydrates like whole grains, fruits, and vegetables in your diet. Monitor your carbohydrate intake and try to eat at consistent times each day.',
                'category': 'diabetes',
                'createdDate': datetime(2023, 4, 12),
                'relevantConditions': ['diabetes', 'obesity']
            },
            {
                'id': 'tip-345678',
                'title': 'Respiratory Health',
                'content': 'Avoid smoke and air pollutants. Keep indoor spaces well-ventilated and consider using an air purifier if you have asthma or allergies.',
                'category': 'respiratory',
                'createdDate': datetime(2023, 4, 10),
                'relevantConditions': ['asthma', 'COPD', 'allergies']
            }
        ]
        return health_tips, 200
    
    @health_tip_ns.doc('create_health_tip')
    @health_tip_ns.expect(health_tip_model)
    @health_tip_ns.response(201, 'Health tip created', health_tip_model)
    @health_tip_ns.response(403, 'Only doctors can create health tips')
    @jwt_optional
    def post(self):
        """Create a new health tip (doctor only)"""
        # For Swagger testing, we'll use a mock user ID
        try:
            current_user_id = get_jwt_identity()
        except:
            current_user_id = "doc-12345678"
        
        data = request.json
        
        # Create a new health tip
        health_tip = {
            'id': 'tip-' + str(uuid.uuid4())[:6],
            'title': data['title'],
            'content': data['content'],
            'category': data['category'],
            'createdDate': datetime.now(),
            'relevantConditions': data.get('relevantConditions', [])
        }
        
        # In a real app, you would save this to a database
        
        return health_tip, 201

@health_tip_ns.route('/<string:id>')
@health_tip_ns.param('id', 'The health tip identifier', example='tip-123456')
class HealthTip(Resource):
    @health_tip_ns.doc('get_health_tip')
    @health_tip_ns.response(200, 'Success', health_tip_model)
    @health_tip_ns.response(404, 'Health tip not found')
    @jwt_optional
    def get(self, id):
        """Get health tip details by ID"""
        # In a real application, this would fetch from a database
        health_tip = {
            'id': id,
            'title': 'Managing Hypertension',
            'content': 'Regular exercise and reduced salt intake can help manage hypertension. Aim for at least 30 minutes of moderate exercise most days of the week.',
            'category': 'cardiovascular',
            'createdDate': datetime(2023, 4, 15),
            'relevantConditions': ['hypertension', 'heart disease']
        }
        return health_tip, 200

@health_tip_ns.route('/patient/<string:patient_id>')
@health_tip_ns.param('patient_id', 'The patient identifier', example='pat-123456')
class PatientHealthTips(Resource):
    @health_tip_ns.doc('get_patient_health_tips')
    @health_tip_ns.response(200, 'Success', [health_tip_model])
    @jwt_optional
    def get(self, patient_id):
        """Get health tips relevant for a specific patient"""
        # In a real application, this would fetch from a database based on patient's conditions
        health_tips = [
            {
                'id': 'tip-123456',
                'title': 'Managing Hypertension',
                'content': 'Regular exercise and reduced salt intake can help manage hypertension. Aim for at least 30 minutes of moderate exercise most days of the week.',
                'category': 'cardiovascular',
                'createdDate': datetime(2023, 4, 15),
                'relevantConditions': ['hypertension', 'heart disease']
            },
            {
                'id': 'tip-234567',
                'title': 'Stress Management',
                'content': 'Practicing mindfulness meditation for 10-15 minutes daily can help reduce stress and lower blood pressure.',
                'category': 'mental health',
                'createdDate': datetime(2023, 4, 16),
                'relevantConditions': ['hypertension', 'anxiety']
            }
        ]
        return health_tips, 200

# Notification Endpoints
@notification_ns.route('/patient/<string:patient_id>')
@notification_ns.param('patient_id', 'The patient identifier', example='pat-123456')
class PatientNotifications(Resource):
    @notification_ns.doc('get_patient_notifications')
    @notification_ns.response(200, 'Success', [notification_model])
    @jwt_optional
    def get(self, patient_id):
        """Get all medication notifications for a specific patient"""
        # In a real application, this would fetch from a database
        notifications = [
            {
                'id': 'notif-123456',
                'patientId': patient_id,
                'prescriptionId': 'pres-123456',
                'medicineId': 'med-1',
                'medicineName': 'Lisinopril 10mg',
                'scheduledTime': datetime.now().replace(hour=8, minute=0, second=0, microsecond=0),
                'status': 'taken',
                'isRead': False
            },
            {
                'id': 'notif-234567',
                'patientId': patient_id,
                'prescriptionId': 'pres-123456',
                'medicineId': 'med-2',
                'medicineName': 'Hydrochlorothiazide 12.5mg',
                'scheduledTime': datetime.now().replace(hour=8, minute=0, second=0, microsecond=0),
                'status': 'pending',
                'isRead': False
            },
            {
                'id': 'notif-345678',
                'patientId': patient_id,
                'prescriptionId': 'pres-123456',
                'medicineId': 'med-1',
                'medicineName': 'Lisinopril 10mg',
                'scheduledTime': datetime.now().replace(hour=20, minute=0, second=0, microsecond=0),
                'status': 'pending',
                'isRead': False
            }
        ]
        return notifications, 200

@notification_ns.route('/<string:id>/update')
@notification_ns.param('id', 'The notification identifier', example='notif-123456')
class UpdateNotification(Resource):
    @notification_ns.doc('update_notification')
    @notification_ns.expect(notification_update_model)
    @notification_ns.response(200, 'Notification updated', notification_model)
    @notification_ns.response(404, 'Notification not found')
    @jwt_optional
    def put(self, id):
        """Update a notification status (taken, missed) and read status"""
        data = request.json
        
        # In a real application, this would update the database
        notification = {
            'id': id,
            'patientId': 'pat-123456',
            'prescriptionId': 'pres-123456',
            'medicineId': 'med-1',
            'medicineName': 'Lisinopril 10mg',
            'scheduledTime': datetime.now().replace(hour=8, minute=0, second=0, microsecond=0),
            'status': data['status'],
            'isRead': data['isRead']
        }
        
        return notification, 200

@notification_ns.route('/schedule/patient/<string:patient_id>')
@notification_ns.param('patient_id', 'The patient identifier', example='pat-123456')
class PatientMedicationSchedule(Resource):
    @notification_ns.doc('get_patient_medication_schedule')
    @notification_ns.response(200, 'Success')
    @jwt_optional
    def get(self, patient_id):
        """Get the medication schedule for a patient"""
        # In a real application, this would fetch from a database
        schedule = {
            'patient': {
                'id': patient_id,
                'name': 'John Smith'
            },
            'dailySchedule': [
                {
                    'time': '08:00',
                    'medicines': [
                        {
                            'medicineId': 'med-1',
                            'name': 'Lisinopril 10mg',
                            'instructions': 'Take with water'
                        },
                        {
                            'medicineId': 'med-2',
                            'name': 'Hydrochlorothiazide 12.5mg',
                            'instructions': 'Take with food'
                        }
                    ]
                },
                {
                    'time': '13:00',
                    'medicines': [
                        {
                            'medicineId': 'med-3',
                            'name': 'Metformin 500mg',
                            'instructions': 'Take with lunch'
                        }
                    ]
                },
                {
                    'time': '20:00',
                    'medicines': [
                        {
                            'medicineId': 'med-1',
                            'name': 'Lisinopril 10mg',
                            'instructions': 'Take with water'
                        }
                    ]
                }
            ]
        }
        
        return schedule, 200

# Follow-up Endpoints
@followup_ns.route('/')
class FollowUpList(Resource):
    @followup_ns.doc('list_followups')
    @followup_ns.response(200, 'Success', [followup_model])
    @jwt_optional
    def get(self):
        """Get a list of all follow-ups for the authenticated user (doctor or patient)"""
        # For Swagger testing, we'll use a mock user ID
        try:
            current_user_id = get_jwt_identity()
        except:
            current_user_id = "doc-12345678"
        
        # In a real app, you would determine if the user is a doctor or patient
        # and fetch appropriate follow-ups
        
        # Mock data
        followups = [
            {
                'id': 'follow-123456',
                'prescriptionId': 'pres-123456',
                'doctorId': 'doc-12345678',
                'patientId': 'pat-12345678',
                'scheduledDate': datetime(2023, 5, 18, 10, 30),
                'status': 'scheduled',
                'notes': 'Review blood pressure readings'
            },
            {
                'id': 'follow-234567',
                'prescriptionId': 'pres-789012',
                'doctorId': 'doc-87654321',
                'patientId': 'pat-12345678',
                'scheduledDate': datetime(2023, 4, 10, 9, 0),
                'status': 'completed',
                'notes': 'Follow-up for upper respiratory infection. Patient has recovered.'
            }
        ]
        
        return followups, 200

@followup_ns.route('/doctor/<string:doctor_id>')
@followup_ns.param('doctor_id', 'The doctor identifier', example='doc-12345678')
class DoctorFollowUps(Resource):
    @followup_ns.doc('get_doctor_followups')
    @followup_ns.response(200, 'Success', [followup_model])
    @jwt_optional
    def get(self, doctor_id):
        """Get all follow-ups for a specific doctor"""
        # In a real application, this would fetch from a database
        followups = [
            {
                'id': 'follow-123456',
                'prescriptionId': 'pres-123456',
                'doctorId': doctor_id,
                'patientId': 'pat-12345678',
                'scheduledDate': datetime(2023, 5, 18, 10, 30),
                'status': 'scheduled',
                'notes': 'Review blood pressure readings'
            },
            {
                'id': 'follow-234567',
                'prescriptionId': 'pres-456789',
                'doctorId': doctor_id,
                'patientId': 'pat-87654321',
                'scheduledDate': datetime(2023, 5, 20, 14, 0),
                'status': 'scheduled',
                'notes': 'Follow-up for cardiac arrhythmia'
            }
        ]
        
        return followups, 200

@followup_ns.route('/doctor/<string:doctor_id>/due')
@followup_ns.param('doctor_id', 'The doctor identifier', example='doc-12345678')
class DoctorDueFollowUps(Resource):
    @followup_ns.doc('get_doctor_due_followups')
    @followup_ns.response(200, 'Success', [followup_model])
    @jwt_optional
    def get(self, doctor_id):
        """Get all due follow-ups for a specific doctor (scheduled within the next 7 days)"""
        # In a real application, this would fetch from a database with date filtering
        next_week = datetime.now() + timedelta(days=7)
        
        # Mock data - assume these are within the next 7 days
        followups = [
            {
                'id': 'follow-123456',
                'prescriptionId': 'pres-123456',
                'doctorId': doctor_id,
                'patientId': 'pat-12345678',
                'patientName': 'John Smith',  # Added patient name for UI display
                'scheduledDate': datetime.now() + timedelta(days=2),
                'status': 'scheduled',
                'notes': 'Review blood pressure readings'
            },
            {
                'id': 'follow-234567',
                'prescriptionId': 'pres-456789',
                'doctorId': doctor_id,
                'patientId': 'pat-87654321',
                'patientName': 'Emma Wilson',  # Added patient name for UI display
                'scheduledDate': datetime.now() + timedelta(days=5),
                'status': 'scheduled',
                'notes': 'Follow-up for cardiac arrhythmia'
            }
        ]
        
        return followups, 200

@followup_ns.route('/patient/<string:patient_id>')
@followup_ns.param('patient_id', 'The patient identifier', example='pat-12345678')
class PatientFollowUps(Resource):
    @followup_ns.doc('get_patient_followups')
    @followup_ns.response(200, 'Success', [followup_model])
    @jwt_optional
    def get(self, patient_id):
        """Get all follow-ups for a specific patient"""
        # In a real application, this would fetch from a database
        followups = [
            {
                'id': 'follow-123456',
                'prescriptionId': 'pres-123456',
                'doctorId': 'doc-12345678',
                'doctorName': 'Dr. Sarah Williams',  # Added doctor name for UI display
                'patientId': patient_id,
                'scheduledDate': datetime(2023, 5, 18, 10, 30),
                'status': 'scheduled',
                'notes': 'Review blood pressure readings'
            },
            {
                'id': 'follow-234567',
                'prescriptionId': 'pres-789012',
                'doctorId': 'doc-87654321',
                'doctorName': 'Dr. Michael Chen',  # Added doctor name for UI display
                'patientId': patient_id,
                'scheduledDate': datetime(2023, 4, 10, 9, 0),
                'status': 'completed',
                'notes': 'Follow-up for upper respiratory infection'
            }
        ]
        
        return followups, 200

@followup_ns.route('/<string:id>/update')
@followup_ns.param('id', 'The follow-up identifier', example='follow-123456')
class UpdateFollowUp(Resource):
    @followup_ns.doc('update_followup')
    @followup_ns.expect(followup_update_model)
    @followup_ns.response(200, 'Follow-up updated', followup_model)
    @followup_ns.response(404, 'Follow-up not found')
    @jwt_optional
    def put(self, id):
        """Update a follow-up status (completed, rescheduled, missed)"""
        data = request.json
        
        # In a real application, this would update the database
        followup = {
            'id': id,
            'prescriptionId': 'pres-123456',
            'doctorId': 'doc-12345678',
            'patientId': 'pat-12345678',
            'scheduledDate': data.get('scheduledDate', datetime(2023, 5, 18, 10, 30)),
            'status': data['status'],
            'notes': data.get('notes', 'Review blood pressure readings')
        }
        
        return followup, 200

# Enhanced Medicine Endpoints
@medicine_ns.route('/groups')
class MedicineGroups(Resource):
    @medicine_ns.doc('list_medicine_groups')
    @medicine_ns.response(200, 'Success')
    @jwt_optional
    def get(self):
        """Get a list of all medicine therapeutic groups"""
        # In a real application, this would fetch from a database
        groups = [
            "ACE Inhibitor",
            "Angiotensin II Receptor Blocker (ARB)",
            "Antibiotic",
            "Anticoagulant",
            "Antiplatelet",
            "Beta Blocker",
            "Calcium Channel Blocker",
            "Diuretic",
            "Statin",
            "Non-Steroidal Anti-Inflammatory Drug (NSAID)",
            "Proton Pump Inhibitor",
            "Selective Serotonin Reuptake Inhibitor (SSRI)"
        ]
        
        return {"groups": groups}, 200

@medicine_ns.route('/companies')
class MedicineCompanies(Resource):
    @medicine_ns.doc('list_medicine_companies')
    @medicine_ns.response(200, 'Success')
    @jwt_optional
    def get(self):
        """Get a list of all pharmaceutical companies"""
        # In a real application, this would fetch from a database
        companies = [
            "AstraZeneca",
            "Bayer",
            "Bristol-Myers Squibb",
            "GlaxoSmithKline",
            "Johnson & Johnson",
            "Merck",
            "Novartis",
            "Pfizer",
            "Roche",
            "Sanofi"
        ]
        
        return {"companies": companies}, 200

@medicine_ns.route('/by-group/<string:group>')
@medicine_ns.param('group', 'The medicine group/therapeutic class', example='ACE Inhibitor')
class MedicinesByGroup(Resource):
    @medicine_ns.doc('get_medicines_by_group')
    @medicine_ns.response(200, 'Success', [medicine_extended_model])
    @jwt_optional
    def get(self, group):
        """Get all medicines in a specific therapeutic group"""
        # In a real application, this would fetch from a database filtered by group
        
        # Mock data for ACE Inhibitors
        if group == "ACE Inhibitor":
            medicines = [
                {
                    'id': 'med-9',
                    'name': 'Lisinopril 5mg',
                    'group': 'ACE Inhibitor',
                    'company': 'AstraZeneca',
                    'description': 'Used to treat high blood pressure and heart failure'
                },
                {
                    'id': 'med-10',
                    'name': 'Lisinopril 10mg',
                    'group': 'ACE Inhibitor',
                    'company': 'AstraZeneca',
                    'description': 'Used to treat high blood pressure and heart failure'
                },
                {
                    'id': 'med-11',
                    'name': 'Lisinopril 20mg',
                    'group': 'ACE Inhibitor',
                    'company': 'AstraZeneca',
                    'description': 'Used to treat high blood pressure and heart failure'
                },
                {
                    'id': 'med-15',
                    'name': 'Enalapril 5mg',
                    'group': 'ACE Inhibitor',
                    'company': 'Merck',
                    'description': 'Used to treat high blood pressure, diabetic kidney disease, and heart failure'
                }
            ]
        # Mock data for Statins
        elif group == "Statin":
            medicines = [
                {
                    'id': 'med-5',
                    'name': 'Atorvastatin 10mg',
                    'group': 'Statin',
                    'company': 'Pfizer',
                    'description': 'Used to lower blood cholesterol levels'
                },
                {
                    'id': 'med-6',
                    'name': 'Atorvastatin 20mg',
                    'group': 'Statin',
                    'company': 'Pfizer',
                    'description': 'Used to lower blood cholesterol levels'
                },
                {
                    'id': 'med-7',
                    'name': 'Atorvastatin 40mg',
                    'group': 'Statin',
                    'company': 'Pfizer',
                    'description': 'Used to lower blood cholesterol levels'
                },
                {
                    'id': 'med-8',
                    'name': 'Atorvastatin 80mg',
                    'group': 'Statin',
                    'company': 'Pfizer',
                    'description': 'Used to lower blood cholesterol levels'
                }
            ]
        # Default empty response for other groups
        else:
            medicines = []
        
        return medicines, 200

@medicine_ns.route('/by-company/<string:company>')
@medicine_ns.param('company', 'The pharmaceutical company', example='AstraZeneca')
class MedicinesByCompany(Resource):
    @medicine_ns.doc('get_medicines_by_company')
    @medicine_ns.response(200, 'Success', [medicine_extended_model])
    @jwt_optional
    def get(self, company):
        """Get all medicines from a specific pharmaceutical company"""
        # In a real application, this would fetch from a database filtered by company
        
        # Mock data for AstraZeneca
        if company == "AstraZeneca":
            medicines = [
                {
                    'id': 'med-9',
                    'name': 'Lisinopril 5mg',
                    'group': 'ACE Inhibitor',
                    'company': 'AstraZeneca',
                    'description': 'Used to treat high blood pressure and heart failure'
                },
                {
                    'id': 'med-10',
                    'name': 'Lisinopril 10mg',
                    'group': 'ACE Inhibitor',
                    'company': 'AstraZeneca',
                    'description': 'Used to treat high blood pressure and heart failure'
                },
                {
                    'id': 'med-11',
                    'name': 'Lisinopril 20mg',
                    'group': 'ACE Inhibitor',
                    'company': 'AstraZeneca',
                    'description': 'Used to treat high blood pressure and heart failure'
                }
            ]
        # Mock data for Pfizer
        elif company == "Pfizer":
            medicines = [
                {
                    'id': 'med-5',
                    'name': 'Atorvastatin 10mg',
                    'group': 'Statin',
                    'company': 'Pfizer',
                    'description': 'Used to lower blood cholesterol levels'
                },
                {
                    'id': 'med-6',
                    'name': 'Atorvastatin 20mg',
                    'group': 'Statin',
                    'company': 'Pfizer',
                    'description': 'Used to lower blood cholesterol levels'
                },
                {
                    'id': 'med-7',
                    'name': 'Atorvastatin 40mg',
                    'group': 'Statin',
                    'company': 'Pfizer',
                    'description': 'Used to lower blood cholesterol levels'
                },
                {
                    'id': 'med-8',
                    'name': 'Atorvastatin 80mg',
                    'group': 'Statin',
                    'company': 'Pfizer',
                    'description': 'Used to lower blood cholesterol levels'
                }
            ]
        # Default empty response for other companies
        else:
            medicines = []
        
        return medicines, 200
    
    
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
