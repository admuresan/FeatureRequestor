# Feature Requestor

A meta application for gathering and managing feature requests from other applications.

## Overview

Feature Requestor is a platform that allows applications to integrate feature request functionality. Other applications can call an API endpoint to open the feature requests page, and users can browse, create, and manage feature requests across multiple applications.

## Features

- **External API Endpoint**: Other apps can call `/api/open-requests` to open feature requests
- **Public Browsing**: View feature requests without authentication
- **User Authentication**: Sign up, login, email verification
- **Feature Request Management**: Create, view, comment on, and bid on feature requests
- **Payment Integration**: Stripe Connect for handling payments between requesters and developers
- **Messaging System**: Private messaging between users
- **Admin Panel**: Manage apps, users, email configuration, and more

## Quick Start

See [SETUP.md](SETUP.md) for detailed setup instructions.

```bash
# Install dependencies
pip install -r requirements.txt

# Run in development mode
export FLASK_ENV=development
python app.py
```

## Architecture

- **Backend**: Python Flask
- **Frontend**: JavaScript, HTML, CSS
- **Database**: SQLite (stored in `instance/data/`)
- **Payments**: Stripe Connect
- **Email**: SMTP-based (configurable)

See `instructions/architecture` for detailed architecture guidelines.

## Documentation

- [Setup Instructions](SETUP.md)
- [Architecture Guidelines](instructions/architecture)
- [Requirements Overview](instructions/overview)
- [Payment Options](instructions/payment_options.md)

## Development

All application code is in the `app/` folder. The application follows a modular architecture with:
- Models in `app/models/`
- Routes in `app/routes/`
- Templates in `app/templates/`
- Static files in `app/static/`
- Utilities in `app/utils/`

## License

[Add license information here]
