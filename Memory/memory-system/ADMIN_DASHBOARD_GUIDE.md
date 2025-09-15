# Admin Dashboard Guide

## Overview

The Memory App Admin Dashboard is a comprehensive web-based platform management interface that provides administrators with full control over the Memory App ecosystem. This guide covers setup, features, and best practices for using the admin dashboard.

## Table of Contents

1. [Setup Instructions](#setup-instructions)
2. [Authentication](#authentication)
3. [Dashboard Features](#dashboard-features)
4. [User Management](#user-management)
5. [Memory Management](#memory-management)
6. [Analytics](#analytics)
7. [System Monitoring](#system-monitoring)
8. [Configuration](#configuration)
9. [Security](#security)
10. [API Reference](#api-reference)
11. [Troubleshooting](#troubleshooting)

## Setup Instructions

### Prerequisites

- Python 3.8+
- PostgreSQL database
- Admin credentials

### Installation

1. **Start the Webhook Server with Admin Features:**
   ```bash
   cd memory-system
   python webhook_server_complete.py
   ```
   The admin dashboard will be available at: `http://localhost:8080/admin`

2. **Default Admin Credentials:**
   - Username: `admin`
   - Password: `admin123!@#` (Change immediately after first login)

3. **Environment Variables:**
   ```bash
   export ADMIN_JWT_SECRET="your-secret-key-here"
   export ADMIN_DEFAULT_PASSWORD="secure-password"
   export DATABASE_URL="postgresql://..."
   ```

### First-Time Setup

1. Navigate to `http://localhost:8080/admin`
2. Login with default credentials
3. Change admin password immediately
4. Create additional admin users as needed
5. Configure platform settings

## Authentication

### Admin Roles

The admin system supports four role levels:

1. **Super Admin**
   - Full system access
   - Can manage other admins
   - Platform configuration
   - All permissions

2. **Admin**
   - User management
   - Memory management
   - View logs and analytics
   - Send notifications

3. **Moderator**
   - View and moderate content
   - Basic user management
   - View logs

4. **Viewer**
   - Read-only access
   - View statistics and logs

### Login Process

1. Navigate to `/admin`
2. Enter username and password
3. System validates credentials
4. JWT token generated (8-hour validity)
5. Redirected to dashboard

### Session Management

- Sessions expire after 8 hours
- Automatic logout on inactivity
- Token stored in localStorage
- Secure token validation

## Dashboard Features

### Main Dashboard

The main dashboard provides real-time statistics:

- **User Metrics**
  - Total users
  - Active users (24h)
  - New users today
  - User growth chart

- **Memory Statistics**
  - Total memories stored
  - Memories created today
  - Memory activity chart
  - Category distribution

- **System Status**
  - Server health
  - API response times
  - Database connections
  - Error rates

- **Communication Channels**
  - WhatsApp messages
  - Telegram messages
  - SMS count
  - Voice calls

### Real-Time Updates

Dashboard refreshes every 30 seconds with:
- Live user count
- Recent activities
- System alerts
- Performance metrics

## User Management

### User List View

Access via: **Users** tab in sidebar

Features:
- Searchable user list
- Sort by creation date, activity
- Filter by subscription status
- Bulk operations

### User Actions

1. **View Details**
   - User profile information
   - Memory count
   - Recent activity
   - Communication history

2. **Suspend User**
   - Temporarily disable account
   - Provide reason for audit
   - Automatic notification

3. **Activate User**
   - Reactivate suspended accounts
   - Clear suspension reason
   - Restore full access

4. **Export User Data**
   - Download user information
   - Export memories
   - GDPR compliance

### User Search

Search users by:
- Phone number
- Name
- User ID
- Email (if available)

## Memory Management

### Memory Browser

Access via: **Memories** tab in sidebar

Features:
- Grid view of memories
- Category filtering
- Content search
- Quick actions

### Memory Operations

1. **View Memory**
   - Full content display
   - Metadata information
   - User association
   - Creation timestamp

2. **Delete Memory**
   - Permanent deletion
   - Audit log entry
   - Confirmation required
   - Reason documentation

3. **Search Memories**
   - Full-text search
   - Category filter
   - Date range filter
   - User filter

### Content Moderation

- Flag inappropriate content
- Bulk delete operations
- Category reassignment
- Privacy compliance

## Analytics

### Analytics Dashboard

Access via: **Analytics** tab in sidebar

#### Key Metrics

1. **User Engagement**
   - Daily Active Users (DAU)
   - Weekly Active Users (WAU)
   - Monthly Active Users (MAU)
   - Session duration
   - Retention rate

2. **Memory Analytics**
   - Creation patterns
   - Popular categories
   - Storage utilization
   - Access frequency

3. **Platform Usage**
   - API calls per minute
   - Peak usage times
   - Error rates
   - Response times

4. **Channel Distribution**
   - WhatsApp usage
   - Telegram usage
   - SMS usage
   - Voice call statistics

### Custom Reports

Generate reports for:
- User growth
- Memory trends
- Revenue (if applicable)
- System performance

## System Monitoring

### System Logs

Access via: **System Logs** tab in sidebar

#### Log Viewer Features

- Real-time log streaming
- Filter by log level (INFO, WARNING, ERROR)
- Search functionality
- Export logs

#### Log Levels

- **INFO**: General information
- **WARNING**: Potential issues
- **ERROR**: System errors
- **DEBUG**: Detailed debugging

### Audit Logs

Track all admin actions:
- Login attempts
- User modifications
- Memory deletions
- Configuration changes
- Data exports

### Health Monitoring

- Server uptime
- CPU usage
- Memory usage
- Database connections
- API endpoint status

## Configuration

### Platform Settings

Access via: **Configuration** tab in sidebar

#### General Settings

- Platform name
- Maintenance mode
- API rate limits
- Storage limits

#### Feature Toggles

Enable/disable features:
- WhatsApp integration
- Telegram integration
- Voice authentication
- Gaming features
- Subscription system

#### Limits Configuration

- Max memories per user
- Max file size
- Voice duration limits
- API rate limits

### Notification Settings

Configure platform notifications:
- Email templates
- SMS templates
- Push notification settings
- Broadcast messages

## Security

### Security Features

1. **Authentication Security**
   - Secure password hashing
   - JWT token authentication
   - Session timeout
   - Failed login tracking

2. **Authorization**
   - Role-based access control
   - Permission system
   - API endpoint protection
   - Resource-level security

3. **Audit Trail**
   - All admin actions logged
   - Timestamp and IP tracking
   - Action details stored
   - Exportable audit logs

4. **IP Whitelisting** (Optional)
   - Restrict admin access by IP
   - Configure allowed IP ranges
   - Bypass for super admins

5. **Two-Factor Authentication** (Planned)
   - TOTP support
   - Backup codes
   - Recovery options

### Security Best Practices

1. **Password Policy**
   - Minimum 12 characters
   - Include uppercase, lowercase, numbers, symbols
   - Regular password rotation
   - No password reuse

2. **Access Control**
   - Principle of least privilege
   - Regular permission reviews
   - Remove inactive admins
   - Monitor admin activities

3. **Data Protection**
   - Encrypt sensitive data
   - Secure API endpoints
   - HTTPS only
   - Regular security audits

## API Reference

### Authentication Endpoints

```
POST /api/admin/login
Body: { username, password }
Response: { token, admin }

POST /api/admin/logout
Headers: Authorization: Bearer <token>
Response: { success }

GET /api/admin/profile
Headers: Authorization: Bearer <token>
Response: { admin_id, role, expires_at }
```

### Dashboard Endpoints

```
GET /api/admin/dashboard
Headers: Authorization: Bearer <token>
Response: { users, memories, system, communications }

GET /api/admin/dashboard/realtime
Headers: Authorization: Bearer <token>
Response: { users_online, active_sessions, api_calls }
```

### User Management Endpoints

```
GET /api/admin/users
Params: ?limit=100&offset=0&search=term
Headers: Authorization: Bearer <token>
Response: { users[], total }

GET /api/admin/users/:id
Headers: Authorization: Bearer <token>
Response: { user, memories, stats }

POST /api/admin/users/:id/suspend
Headers: Authorization: Bearer <token>
Body: { reason }
Response: { success }

POST /api/admin/users/:id/activate
Headers: Authorization: Bearer <token>
Response: { success }
```

### Memory Management Endpoints

```
GET /api/admin/memories
Params: ?limit=100&offset=0&user_id=&search=
Headers: Authorization: Bearer <token>
Response: { memories[], total }

DELETE /api/admin/memories/:id
Headers: Authorization: Bearer <token>
Body: { reason }
Response: { success }
```

### Analytics Endpoints

```
GET /api/admin/analytics
Params: ?period=7days|30days|90days
Headers: Authorization: Bearer <token>
Response: { user_growth, memory_stats, engagement }
```

### System Endpoints

```
GET /api/admin/logs
Params: ?limit=100&level=INFO|WARNING|ERROR
Headers: Authorization: Bearer <token>
Response: { logs[] }

GET /api/admin/audit-logs
Params: ?limit=100&admin_id=
Headers: Authorization: Bearer <token>
Response: { logs[] }
```

### Configuration Endpoints

```
GET /api/admin/config
Headers: Authorization: Bearer <token>
Response: { platform_name, features, limits }

PUT /api/admin/config
Headers: Authorization: Bearer <token>
Body: { platform_name, features, limits }
Response: { success }
```

### Notification Endpoints

```
POST /api/admin/notifications
Headers: Authorization: Bearer <token>
Body: { title, message, target, channels }
Response: { success, sent_to }
```

## Troubleshooting

### Common Issues

#### 1. Cannot Login
- Verify credentials are correct
- Check database connection
- Ensure admin user exists
- Check JWT secret is set

#### 2. Dashboard Not Loading
- Check API endpoints are accessible
- Verify authentication token
- Check browser console for errors
- Ensure CORS is configured

#### 3. Missing Data
- Verify database queries
- Check user permissions
- Ensure data exists in database
- Check API response format

#### 4. Performance Issues
- Monitor database query performance
- Check server resources
- Optimize API endpoints
- Implement caching

### Debug Mode

Enable debug logging:
```python
# In admin_service.py
logging.basicConfig(level=logging.DEBUG)
```

### Support

For issues or questions:
1. Check system logs
2. Review audit logs
3. Consult API documentation
4. Contact system administrator

## Updates and Maintenance

### Regular Maintenance Tasks

1. **Daily**
   - Review system logs
   - Check error rates
   - Monitor user activity

2. **Weekly**
   - Review audit logs
   - Check storage usage
   - Update admin passwords

3. **Monthly**
   - Security audit
   - Performance review
   - Feature usage analysis

### Upgrade Process

1. Backup database
2. Test in staging environment
3. Schedule maintenance window
4. Deploy updates
5. Verify functionality
6. Monitor for issues

## Conclusion

The Admin Dashboard provides comprehensive control over the Memory App platform. Regular monitoring and maintenance ensure optimal performance and security. Always follow security best practices and keep the system updated.

For additional support or feature requests, contact the development team.