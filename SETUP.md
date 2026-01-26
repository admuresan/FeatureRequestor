# Feature Requestor - Setup Instructions

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

## Installation

1. Clone or navigate to the project directory:
   ```bash
   cd FeatureRequestor
   ```

2. Create a virtual environment (recommended):
   ```bash
   python -m venv venv
   ```

3. Activate the virtual environment:
   - On Windows:
     ```bash
     venv\Scripts\activate
     ```
   - On Linux/Mac:
     ```bash
     source venv/bin/activate
     ```

4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

5. Set up environment variables (optional, for production):
   Create a `.env` file in the project root:
   ```
   SECRET_KEY=your-secret-key-here
   ADMIN_USERNAME=LastTerminal
   ADMIN_PASSWORD=WhiteMage
   SERVER_PORT=6003
   ```

## Running the Application

### Development Mode

Set the environment variable and run:
```bash
export FLASK_ENV=development  # On Windows: set FLASK_ENV=development
python app.py
```

Or:
```bash
export DEV_MODE=true  # On Windows: set DEV_MODE=true
python app.py
```

The application will run on `http://localhost:6003` (or the port specified in `ssh/deploy_config.json`).

### Production Mode

Run without setting DEV_MODE:
```bash
python app.py
```

For production, it's recommended to use a production WSGI server like Gunicorn:
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:6003 app:create_app()
```

## Initial Setup

On first launch, the application will:
1. Create the database in `instance/data/feature_requestor.db`
2. Create a default admin account:
   - Email: `admin@feature-requestor.com`
   - Username: `LastTerminal` (or from ADMIN_USERNAME env var)
   - Password: `WhiteMage` (or from ADMIN_PASSWORD env var)
3. Create the "Feature Requestor" app in the app registry

## Configuration

Configuration files are stored in the `instance/` folder (not git-backed):

- `instance/config.json` - Application configuration
- `instance/email_config.json` - Email/SMTP configuration
- `instance/email_templates.json` - Email templates
- `instance/data/` - Database files
- `instance/uploads/` - User uploads

## Email Configuration

To enable email functionality, configure SMTP settings in the admin panel or edit `instance/email_config.json`:

```json
{
  "from_email_mask": "noreply@feature-requestor.com",
  "smtp_host": "smtp.gmail.com",
  "smtp_port": 587,
  "smtp_security": "TLS",
  "smtp_username": "your-email@gmail.com",
  "smtp_password": "your-app-password"
}
```

## Stripe Configuration

For payment functionality, set up Stripe API keys as environment variables:
```
STRIPE_PUBLIC_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

## Troubleshooting

- **Database errors**: Ensure the `instance/data/` directory exists and is writable
- **Email not sending**: Check SMTP configuration in admin panel
- **Port already in use**: Change the port in `ssh/deploy_config.json` or set `SERVER_PORT` environment variable

