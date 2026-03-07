# Mini Cloud Storage 2.0

A full-stack cloud storage application built with Flask, PostgreSQL, and MinIO.

## Features

### User Features
- **Registration & Login** - With image-based captcha verification
- **Profile Management** - Update username, email, password, and profile photo
- **File Upload** - Drag & drop, camera, or browse upload with metadata (name, category, visibility)
- **File Management** - Create, read, update, delete files with visibility control:
  - **Public** - Visible and downloadable by everyone
  - **Private** - Only visible to owner
  - **Semi-Public** - Only visible to users you share with
- **Search** - Search files by name or category
- **Download** - Download files with tracking

### Admin Features
- **Dashboard** - Statistics and overview
- **User Management** - Full CRUD operations on users
- **File Management** - Delete any file
- **Activity Logs** - Comprehensive logging for debugging
- **Monitoring** - Track user activity and system usage

## Architecture

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Frontend   │───▶│   Backend   │───▶│     API     │
│  (Flask)    │    │  (Flask)    │    │   (Flask)   │
│  Port 5000  │    │  Port 5001  │    │  Port 8080  │
└─────────────┘    └─────────────┘    └──────┬──────┘
                                             │
                    ┌────────────────────────┼────────────────────────┐
                    ▼                        ▼                        ▼
             ┌────────────┐          ┌────────────┐          ┌────────────┐
             │ PostgreSQL │          │   MinIO    │          │   Logs     │
             │   :5432    │          │   :9000    │          │  Volume    │
             └────────────┘          └────────────┘          └────────────┘
```

## Tech Stack

- **Frontend**: Flask + Bootstrap 5
- **Backend**: Flask (API Proxy)
- **API**: Flask REST API
- **Database**: PostgreSQL 15
- **Object Storage**: MinIO
- **Authentication**: JWT
- **Password Hashing**: bcrypt
- **Captcha**: Custom image-based captcha with PIL

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Git

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/kaguai10/cloud-storage2.git
cd cloud-storage2
```

2. **Configure environment variables**
```bash
cp .env.example .env
# Edit .env with your settings
```

3. **Start all services**

**Important**: MinIO requires the password to be at least 8 characters. If you get MinIO errors, export the environment variables first:

```bash
export MINIO_ROOT_USER=adminminio
export MINIO_ROOT_PASSWORD=MinioSecret2026!
docker-compose up -d
```

4. **Access the application**
- **Frontend**: http://localhost:5000
- **Backend**: http://localhost:5001
- **API**: http://localhost:8080
- **MinIO Console**: http://localhost:9001 (adminminio / MinioSecret2026!)

### Default Admin Account
- **Username**: `admin`
- **Password**: `admin123`

> ⚠️ **IMPORTANT**: Change the default admin password immediately after first login!

### Stop services
```bash
docker-compose down
```

### Stop and remove volumes
```bash
docker-compose down -v
```

## Project Structure

```
cloud-storage2/
├── api/                    # REST API service
│   ├── app.py             # Main application
│   ├── config.py          # Configuration
│   ├── models.py          # SQLAlchemy models
│   ├── database.py        # Database setup
│   ├── health.py          # Health check endpoint
│   ├── requirements.txt   # Python dependencies
│   ├── Dockerfile
│   ├── routes/            # API routes
│   │   ├── auth.py        # Authentication routes
│   │   ├── users.py       # User management routes
│   │   ├── admin.py       # Admin routes
│   │   ├── files.py       # File management routes
│   │   └── search.py      # Search routes
│   ├── services/          # Business logic
│   │   ├── auth_service.py
│   │   └── storage.py
│   └── utils/             # Utilities
│       ├── captcha.py
│       ├── validator.py
│       ├── logger.py
│       └── crypto.py
├── backend/               # Backend proxy service
│   ├── app.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/              # Frontend web service
│   ├── app.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── templates/         # Jinja2 templates
│       ├── base.html
│       ├── home.html
│       ├── login.html
│       ├── register.html
│       ├── settings.html
│       ├── upload.html
│       ├── search.html
│       ├── my_files.html
│       ├── file_*.html
│       └── admin/
├── docker-compose.yml
└── .env
```

## API Endpoints

### Authentication
- `GET /api/auth/captcha` - Get captcha image
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - User login

### Users
- `GET /api/users/me` - Get current user
- `PUT /api/users/me` - Update profile
- `PUT /api/users/me/password` - Change password
- `PUT /api/users/me/photo` - Update profile photo

### Files
- `POST /api/files/upload` - Upload file
- `GET /api/files/my-files` - Get user's files
- `GET /api/files/<id>` - Get file details
- `PUT /api/files/<id>` - Update file
- `DELETE /api/files/<id>` - Delete file
- `GET /api/files/<id>/download` - Download file
- `POST /api/files/<id>/share` - Share file

### Search
- `GET /api/search` - Search files (auth required)
- `GET /api/search/public` - Search public files

### Admin
- `GET /api/admin/dashboard` - Dashboard stats
- `GET /api/admin/users` - List all users
- `DELETE /api/admin/users/<id>` - Delete user
- `GET /api/admin/logs` - Activity logs
- `GET /api/admin/files` - List all files
- `DELETE /api/admin/files/<id>` - Delete any file

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `FLASK_ENV` | Flask environment | `development` |
| `SECRET_KEY` | Flask secret key | (required) |
| `JWT_SECRET` | JWT signing secret | (required) |
| `POSTGRES_USER` | Database user | `clouduserdb` |
| `POSTGRES_PASSWORD` | Database password | (required) |
| `POSTGRES_DB` | Database name | `clouddb` |
| `POSTGRES_HOST` | Database host | `db` |
| `MINIO_ROOT_USER` | MinIO admin user | `adminminio` |
| `MINIO_ROOT_PASSWORD` | MinIO admin password | (required) |
| `MINIO_ENDPOINT` | MinIO endpoint | `minio:9000` |
| `MINIO_BUCKET` | MinIO bucket name | `cloud-storage` |
| `MAX_UPLOAD_SIZE` | Max file size (bytes) | `52428800` (50MB) |
| `LOG_LEVEL` | Logging level | `INFO` |

## Security Notes

1. Change default passwords in `.env` before production
2. Use HTTPS in production
3. Keep `SECRET_KEY` and `JWT_SECRET` secure
4. Regularly backup PostgreSQL data and MinIO storage

## License

MIT License

## Author

kaguai10
