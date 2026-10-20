# Acrylic Platform - Developer Documentation

## Overview

Acrylic Platform is a Django-based web backend application that facilitates music licensing between artists and buyers. The platform allows artists to upload their tracks, manage licensing terms, and handle split sheets for royalty distribution, while buyers can browse, license, and purchase music for various uses. The application exposes an API that is used by the frontend web application.

- Acrylic Back Office: https://platform.acrylic.la/admin
- Acrylic API: https://platform.acrylic.la/api/v1/schema/swagger/


## Table of Contents

- [Project Architecture](#project-architecture)
- [Installation & Setup](#installation--setup)
- [Project Structure](#project-structure)
- [Core Applications](#core-applications)
- [API Documentation](#api-documentation)
- [Database Models](#database-models)
- [Authentication & Authorization](#authentication--authorization)
- [File Storage](#file-storage)
- [External Integrations](#external-integrations)
- [Background Tasks](#background-tasks)
- [Development Guidelines](#development-guidelines)
- [Deployment](#deployment)

## Project Architecture

### Technology Stack

- **Backend Framework**: Django 5.0.6
- **API Framework**: Django REST Framework 3.14.0
- **Database**: PostgreSQL (production) / SQLite (development)
- **Authentication**: JWT tokens, Social Auth (Spotify, Facebook, Google)
- **File Storage**: AWS S3
- **Email**: AWS SES
- **Background Tasks**: Celery with Redis
- **API Documentation**: drf-spectacular (OpenAPI/Swagger)
- **Frontend Integration**: CORS-enabled for Angular frontend

### System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Angular       │    │   Django REST    │    │   PostgreSQL    │
│   Frontend      │◄──►│   API Backend    │◄──►│   Database      │
│   (External)    │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │   External APIs  │
                       │   - Spotify      │
                       │   - Chartmetric  │
                       │   - SignWell     │
                       │   - HubSpot      │
                       └──────────────────┘
```

## Installation & Setup

### Prerequisites

- Python 3.11+
- PostgreSQL (for production)
- Redis (for Celery)
- AWS Account (for S3 storage and SES email)

### Local Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd acrylic
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Configuration**
   Create a `.env` file in the project root:
   ```env
   SECRET_KEY=your-secret-key
   DEBUG=True
   DATABASE_URL=sqlite:///db.sqlite3

   # AWS Configuration
   AWS_ACCESS_KEY_ID=your-aws-access-key
   AWS_SECRET_ACCESS_KEY=your-aws-secret-key
   AWS_STORAGE_BUCKET_NAME=your-s3-bucket
   AWS_S3_REGION_NAME=us-east-1

   # Email Configuration
   EMAIL_HOST=your-smtp-host
   EMAIL_HOST_USER=your-email-user
   EMAIL_HOST_PASSWORD=your-email-password
   EMAIL_FROM=noreply@acrylic.la

   # External API Keys
   SPOTIFY_CLIENT_ID=your-spotify-client-id
   SPOTIFY_CLIENT_SECRET=your-spotify-client-secret
   CHARTMETRIC_REFRESH_TOKEN=your-chartmetric-token
   SIGNWELL_API_KEY=your-signwell-api-key
   HUBSPOT_ACCESS_TOKEN=your-hubspot-token
   ```

5. **Database Setup**
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

6. **Run Development Server**
   ```bash
   python manage.py runserver
   ```

7. **Access the Application**
   - Admin Panel: http://127.0.0.1:8000/admin/
   - API Documentation: http://127.0.0.1:8000/api/v1/schema/swagger/

## Project Structure

```
acrylic/
├── account/           # User accounts and authentication
├── artist/            # Artist profiles and management
├── buyer/             # Buyer profiles and tiers
├── catalog/           # Music catalog (tracks, genres, pricing)
├── legal/             # Split sheets and contracts
├── content/           # CMS content (articles)
├── common/            # Shared utilities and base models
├── chartmetric/       # Chartmetric API integration
├── spotify/           # Spotify API integration
├── billing/           # Billing and payments (future)
├── distributor/       # Music distributors (future)
├── acrylic/           # Django project settings
├── staticfiles/       # Static files
├── documents/         # File uploads
└── docs/              # Project documentation
```

## Core Applications

### Account App
**Purpose**: User account management, authentication, and document handling

**Key Models**:
- `Account`: Extended user profile with billing information
- `Document`: File uploads with digital signature support
- `Invitation`: User invitation system

**Key Features**:
- JWT authentication
- Social authentication (Spotify, Facebook, Google)
- Document management with SignWell integration
- User registration and email verification

### Artist App
**Purpose**: Artist profile management and statistics

**Key Models**:
- `Artist`: Artist profiles with social media links and statistics

**Key Features**:
- Artist profile creation and management
- Social media integration
- Spotify and Chartmetric statistics tracking
- Automatic slug generation for public profiles
- KAMRank ranking system

### Catalog App
**Purpose**: Music catalog management and pricing

**Key Models**:
- `Track`: Music tracks with metadata and files
- `Genre`: Music genres
- `Price`: Pricing tiers for tracks
- `TierPrice`: Tier-specific pricing
- `SyncList`: Curated track collections
- `Distributor`: Music distribution companies

**Key Features**:
- Track upload and metadata management
- Multi-file support (WAV, MP3, snippets)
- Genre and tag management
- Dynamic pricing based on buyer tiers
- Sync lists for playlist-like collections
- Automatic Spotify/Chartmetric ID resolution

### Buyer App
**Purpose**: Music buyer management and access control

**Key Models**:
- `Buyer`: Buyer profiles
- `Tier`: Buyer access tiers

**Key Features**:
- Tier-based access control
- Dynamic pricing based on tier level

### Legal App
**Purpose**: Split sheet management and digital signatures

**Key Models**:
- `SplitSheet`: Revenue split agreements
- `PublishingSplit`: Publishing rights splits
- `MasterSplit`: Master recording splits

**Key Features**:
- Digital signature workflow via SignWell
- Publishing and master rights management
- Automatic signature request generation
- Webhook handling for signature updates

## API Documentation

### Base URL
- **Production**: `https://platform.acrylic.la/api/v1/`
- **Development**: `http://127.0.0.1:8000/api/v1/`

### Authentication

The API uses JWT (JSON Web Tokens) for authentication:

```bash
# Obtain token
POST /api/v1/auth/token/
{
  "email": "user@example.com",
  "password": "password"
}

# Use token in subsequent requests
Authorization: Bearer <access_token>
```

### Key Endpoints

#### Public Endpoints
- `GET /artists/` - List artists
- `GET /tracks/` - List tracks
- `GET /genres/` - List genres
- `GET /synclists/` - List sync lists
- `GET /prices/` - List pricing tiers

#### Artist Endpoints (Authenticated)
- `GET /my-artist/` - Artist profile
- `GET/POST /my-artist/tracks/` - Artist's tracks
- `GET/POST /my-artist/synclists/` - Artist's sync lists
- `GET/POST /my-artist/split-sheets/` - Artist's split sheets

#### Account Endpoints (Authenticated)
- `GET/PUT /account/` - User account
- `GET/POST /account/documents/` - User documents

### API Schema
Full API documentation is available at `/api/v1/schema/swagger/` when running the development server.

## Database Models

### Base Model
All models inherit from `BaseModel` which provides:
- `uuid`: UUID primary key
- `created`: Timestamp of creation
- `updated`: Timestamp of last update
- Automatic indexing on UUID, created, and updated fields

### Key Relationships

```mermaid
erDiagram
    User ||--o| Account : has
    User ||--o| Artist : has
    User ||--o| Buyer : has
    Artist ||--o{ Track : owns
    Track ||--o| SplitSheet : has
    SplitSheet ||--o{ PublishingSplit : contains
    SplitSheet ||--o{ MasterSplit : contains
    Buyer }o--|| Tier : belongs_to
    Track }o--|| Price : has
    Price ||--o{ TierPrice : has
```

### Data Validation
- ISRC codes are validated using custom validators
- Email fields use Django's built-in email validation
- Percentage fields are validated to ensure they sum to 100%

## Authentication & Authorization

### Authentication Methods
1. **JWT Tokens**: Primary authentication method
2. **Social Auth**: Integration with Spotify, Facebook, Google
3. **Email/Password**: Traditional authentication

### Permission System
- **IsAuthenticated**: Required for most endpoints
- **Custom Permissions**: Artist-specific and buyer-specific views
- **Admin Permissions**: Django admin interface

### User Types
Users can have multiple roles:
- **Artist**: Can upload tracks and manage split sheets
- **Buyer**: Can license tracks based on tier
- **Admin**: Full system access

## File Storage

### AWS S3 Integration
- **Default Storage**: Private S3 bucket for user uploads
- **Public Storage**: Public S3 bucket for publicly accessible files
- **Static Files**: Served via WhiteNoise in production

### File Types
- **Audio Files**: WAV, MP3 (tracks and snippets)
- **Images**: Artist photos, track covers, sync list covers
- **Documents**: PDFs, contracts, split sheets

### File Upload Process
1. Files are uploaded directly to S3 via `s3file` middleware
2. Database records store S3 file paths
3. Presigned URLs provide secure temporary access

## External Integrations

### Spotify API
- **Purpose**: Track metadata enrichment, artist statistics
- **Implementation**: `spotify/` app with async tasks
- **Data Sync**: Automatic track ID resolution and metadata updates

### Chartmetric API
- **Purpose**: Music industry analytics and statistics
- **Implementation**: `chartmetric/` app with periodic data updates
- **Data Tracked**: Follower counts, popularity metrics

### SignWell (Digital Signatures)
- **Purpose**: Legal document signing workflow
- **Implementation**: `legal/` app with webhook handling
- **Process**: Document generation → Signature request → Webhook updates

### HubSpot CRM
- **Purpose**: Customer relationship management
- **Implementation**: Artist profile synchronization
- **Data Sync**: Artist contact information and engagement tracking

## Background Tasks

### Celery Configuration
Background tasks are handled by Celery with Redis as the message broker.

### Task Categories

#### Data Synchronization Tasks
- `load_spotify_id`: Resolve Spotify IDs for tracks
- `load_chartmetric_ids`: Resolve Chartmetric IDs
- `update_kamrank`: Update artist ranking

#### Legal Process Tasks
- `request_signatures_task`: Send signature requests via SignWell
- `split_sheet_load_spotify_data_task`: Load track data for split sheets

#### Notification Tasks
- Email notifications for various events
- Webhook processing tasks

### Running Celery
```bash
# Start Celery worker
celery -A acrylic worker -l info

# Start Celery beat (for scheduled tasks)
celery -A acrylic beat -l info
```

## Development Guidelines

### Model Guidelines
- Always inherit from `BaseModel` for new models
- Add appropriate indexes for performance
- Use descriptive field names and help text
- Implement `__str__` methods for all models

### API Guidelines
- Use Django REST Framework serializers
- Implement proper permission classes
- Add pagination for list endpoints
- Include comprehensive API documentation


## Deployment

### Heroku Deployment

The application is configured for Heroku deployment with:

1. **Procfile**: Defines web and worker processes
2. **runtime.txt**: Specifies Python version
3. **django-heroku**: Automatic Heroku configuration
4. **Gunicorn**: WSGI server for production

### Environment Variables

Required production environment variables:
```env
SECRET_KEY=production-secret-key
DEBUG=False
DATABASE_URL=postgresql://...
SENTRY_DSN=https://...
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
# ... (all other environment variables from development)
```

### Database Migrations
```bash
# Run migrations on deployment
heroku run python manage.py migrate

# Create superuser (if needed)
heroku run python manage.py createsuperuser
```

### Monitoring

- **Error Tracking**: Sentry integration for error monitoring
- **Logs**: Heroku logs for application monitoring


# Manual de integración de búsquedas AIMS

Este documento describe los endpoints AIMS expuestos por Acrylic. El backend actúa como proxy: conserva las credenciales de AIMS en el servidor, enriquece los resultados con datos del catálogo de Acrylic y devuelve un formato común al cliente.

## Inicio rápido

Base URL:

- Producción: `https://platform.acrylic.la/api/v1`
- Desarrollo: `http://127.0.0.1:8000/api/v1`

Todos los endpoints de este documento requieren autenticación, excepto el webhook. Enviar el access token JWT en cada petición:

```http
Authorization: Bearer <access_token>
```

Las peticiones y respuestas JSON usan:

```http
Content-Type: application/json
```

Orden recomendado de integración:

1. Implementar búsqueda por prompt.
2. Implementar búsqueda por enlace con un solo endpoint para Spotify y YouTube.
3. Implementar video en dos pasos: carga y búsqueda por `hash`.
4. Agregar carga multipart únicamente para archivos que no convenga enviar a través del servidor web.

## Resumen de endpoints

| Método | Ruta | Uso |
| --- | --- | --- |
| `POST` | `/aims/similarity-prompt/` | Buscar mediante texto libre |
| `POST` | `/aims/similarity/` | Buscar mediante enlace de Spotify o YouTube |
| `POST` | `/aims/similarity/spotify/` | Alias explícito para Spotify |
| `POST` | `/aims/similarity-video-upload/` | Subir video y obtener su `hash` |
| `POST` | `/aims/similarity-video-search/` | Buscar mediante un `hash` de video |
| `POST` | `/aims/similarity-video/` | Cargar y buscar video en una petición (compatibilidad) |
| `POST` | `/aims/video-multipart/initiate/` | Iniciar una carga multipart a S3 |
| `POST` | `/aims/video-multipart/presign-parts/` | Obtener URLs para las partes |
| `POST` | `/aims/video-multipart/complete/` | Completar la carga y ejecutar la búsqueda |
| `POST` | `/aims/video-multipart/abort/` | Cancelar una carga multipart |
| `POST` | `/aims/download-url/` | Crear una URL temporal para descargar una pista |
| `POST` | `/aims-webhook/` | Recibir el estado de procesamiento de AIMS; ruta no versionada |

## Formato común de resultados

Prompt, YouTube y video devuelven el siguiente contenedor:

```json
{
  "count": 1,
  "results": [
    {
      "id_client": 124,
      "track_id": 31,
      "track_uuid": "4fa8b8c7-6f53-4e70-92b1-5bf6cce2a0c1",
      "track_name": "Example Track",
      "artist_canonical": "Example Artist",
      "artist_country_code2": "MX",
      "match_score": 0.93,
      "duration": 241,
      "release_year": 2024,
      "track_virality": 82.4,
      "extended_commercial_use": false,
      "price_id": 4,
      "price_uuid": "65ac50a0-9c54-4b4e-b425-f2bc63239280",
      "price_description": "Standard license",
      "price_temp": 250.0,
      "youtube_restriction": null,
      "archival": null,
      "moods": ["happy", "energetic"],
      "highlights": [
        {"duration": 12.5, "offset": 30.0}
      ],
      "cover_image": "https://example.com/cover.jpg",
      "file_wav": "https://example.com/track.wav",
      "file_mp3": "https://example.com/track.mp3",
      "waveform": "https://example.com/waveform.json",
      "waveform_url": "https://example.com/waveform.json",
      "track_name_track": "Catalog Track Name",
      "spotify_followers": 34412,
      "instagram_followers": 45123,
      "instagram_url": "https://instagram.com/example",
      "youtube_followers": 32123,
      "tiktok_followers": 14231,
      "chartmetric_instagram_demographics": null,
      "chartmetric_instagram_top_cities": null,
      "chartmetric_instagram_top_countries": null,
      "chartmetric_instagram_sports_fit_percent": 33.33
    }
  ]
}
```

Los campos provenientes del catálogo pueden ser `null` o `0` cuando AIMS devuelve una pista que no se puede relacionar con `Track.aims_id`. `waveform` y `waveform_url` contienen el mismo valor por compatibilidad.

## 1. Búsqueda por prompt

`POST /aims/similarity-prompt/`

Busca pistas a partir de una descripción en lenguaje natural.

### Body

| Campo | Tipo | Obligatorio | Default | Descripción |
| --- | --- | --- | --- | --- |
| `text` | string | Sí | — | Prompt de búsqueda |
| `page` | integer | No | `1` | Página solicitada a AIMS |
| `page_size` | integer | No | `50` | Cantidad solicitada a AIMS |

`text` también se acepta como query parameter, aunque se recomienda enviarlo en JSON.

```bash
curl -X POST "$BASE_URL/aims/similarity-prompt/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "indie pop alegre, femenino, para un anuncio de verano",
    "page": 1,
    "page_size": 20
  }'
```

Respuesta exitosa: formato común de resultados. Si falta `text`, responde `400`:

```json
{"detail": "text is required"}
```

## 2. Búsqueda por enlace de Spotify o YouTube

`POST /aims/similarity/`

El mismo endpoint acepta uno de estos campos:

| Campo | Tipo | Obligatorio | Descripción |
| --- | --- | --- | --- |
| `spotify_url` | string | Condicional | URL, URI o ID de una pista de Spotify |
| `youtube_url` | string | Condicional | URL de un video de YouTube |
| `page` | integer | No | Página; default `1` |
| `page_size` | integer | No | Solo se aplica a Spotify; default `20` |

Se debe enviar `spotify_url` o `youtube_url`. Si se envían ambos, Spotify tiene prioridad.

### Spotify

Formatos aceptados:

- `https://open.spotify.com/track/<id>`
- `spotify:track:<id>`
- ID crudo de 10 a 40 caracteres alfanuméricos

```bash
curl -X POST "$BASE_URL/aims/similarity/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "spotify_url": "https://open.spotify.com/track/6u6kH7V7Tx5xDJtF82vVw0",
    "page": 1,
    "page_size": 20
  }'
```

La respuesta añade información de la pista semilla:

```json
{
  "exists_in_db": true,
  "track_uuid": "4fa8b8c7-6f53-4e70-92b1-5bf6cce2a0c1",
  "spotify": {
    "spotify_id": "6u6kH7V7Tx5xDJtF82vVw0",
    "isrc": "MXF010700413",
    "name": "Estos Celos",
    "artist": "Vicente Fernandez",
    "artists": ["Vicente Fernandez"],
    "image": "https://i.scdn.co/image/example",
    "url": "https://open.spotify.com/track/6u6kH7V7Tx5xDJtF82vVw0"
  },
  "count": 20,
  "results": [],
  "seed_track": {
    "in_catalog": true,
    "track": {}
  },
  "aims_status_code": 200
}
```

`seed_track.track` usa el mismo esquema que cada elemento de `results` y añade `spotify_id`, `isrc` y `audience_sport_fit_percent`. Si la pista no está en el catálogo, `track` será `null`.

También existe el alias `POST /aims/similarity/spotify/`, que exige `spotify_url` y devuelve la misma estructura.

### YouTube

```bash
curl -X POST "$BASE_URL/aims/similarity/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "page": 1
  }'
```

Respuesta exitosa: formato común de resultados. En la implementación actual, YouTube usa un `page_size` fijo de `20`.

Errores propios de este flujo:

- `400`: falta `youtube_url` o el valor de Spotify no tiene formato válido.
- `502`: falló Spotify, falló AIMS o AIMS devolvió una respuesta que no es JSON.
- `504`: AIMS excedió el tiempo de espera.


## Errores transversales

| Estado | Significado |
| --- | --- |
| `400 Bad Request` | Falta un campo o su formato no es válido |
| `401 Unauthorized` | JWT ausente, inválido o expirado |
| `404 Not Found` | Recurso multipart inexistente para el usuario |
| `409 Conflict` | Estado multipart incompatible con la operación |
| `502 Bad Gateway` | Fallo de AIMS, Spotify o S3, o respuesta externa inválida |
| `504 Gateway Timeout` | AIMS no respondió dentro del timeout |

Los errores usan normalmente esta forma:

```json
{"detail": "Descripción del error"}
```

## Opciones de desarrollo

Los endpoints de similitud aceptan `?dummy=1` para evitar llamadas a AIMS. Además, el prompt exacto `test` devuelve tres resultados ficticios. Estas opciones son provisionales y no deben formar parte del contrato de producción.

`?debug_moods=1` imprime información de moods en el proceso del servidor y tampoco debe usarse como funcionalidad pública.

## Configuración requerida en el backend

```env
AIMS_CLIENT_ID=...
AIMS_API_SECRET=...
AIMS_WEBHOOK_URL=https://api.example.com/aims-webhook/
AIMS_WEBHOOK_SECRET=...
SPOTIFY_CLIENT_ID=...
SPOTIFY_CLIENT_SECRET=...
AWS_STORAGE_BUCKET_NAME=...
AWS_S3_REGION_NAME=...
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
```

Para producción se recomienda configurar explícitamente el secret del webhook y deshabilitar los atajos `dummy`/`test` mediante una bandera de entorno o eliminarlos.