# Digital Magazine Platform

## Architecture Overview

This project is a Digital Magazine Platform built with Django, featuring a unique integration with Supabase for authentication and user management. The architecture is designed to leverage Supabase's auth system while maintaining Django's powerful ORM and model relationships.

### Key Architectural Decision

The core of this architecture lies in using Supabase's `auth.users` table as the User model in Django. This approach allows for:

1. Direct relationships between Supabase-managed users and Django models
2. Utilization of Supabase's authentication system and API
3. Seamless integration between Supabase and Django ecosystems

## Tech Stack

- **Backend**: Django 4.2
- **Authentication**: Supabase + Custom Django Authentication Backend
- **Database**: PostgreSQL (via Supabase)
- **API**: Django REST Framework + Supabase-generated API for user-related operations
- **Task Queue**: Celery with Redis
- **WebSockets**: Django Channels
- **Documentation**: DRF Spectacular

## Key Components

1. **User Management**
   - Custom User model mapped to Supabase's `auth.users` table
   - SupabaseAuthBackend for authentication
   - Direct use of Supabase API for user-related operations

2. **Model Relationships**
   - Django models can directly reference the User model
   - Example: `UserProfile` model with a OneToOne relationship to User

3. **Magazine Management, AI Integration, Payments, etc.**
   (As previously described)

## Authentication Flow

1. Users authenticate using Supabase (email/password or social logins)
2. SupabaseAuthBackend validates credentials against Supabase
3. On successful authentication, a corresponding Django user object is created/retrieved
4. Django sessions and permissions are managed based on Supabase user data

## Database Schema

- `auth.users` table is managed by Supabase
- Django models (including User model) are configured as unmanaged models referencing Supabase tables
- Other Django models can create foreign key relationships to the User model

## API Structure

- Hybrid approach:
  - Supabase-generated API for user-related operations
  - Django REST Framework for all other application-specific endpoints

## Advantages of This Approach

1. **Simplified User Management**: Leverage Supabase's robust auth system while maintaining Django's ORM capabilities
2. **Direct Relationships**: Create Django models with direct foreign key relationships to Supabase-managed users
3. **API Efficiency**: Utilize Supabase's auto-generated APIs for user-related operations, reducing custom API development
4. **Scalability**: Benefit from Supabase's scalable auth system while retaining Django's flexibility for application logic
5. **Reduced Development Time**: Minimize the need for custom user API endpoints

## Example Model Relationship