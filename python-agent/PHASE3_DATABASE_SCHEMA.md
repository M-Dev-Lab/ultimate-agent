"""
Phase 3 Database Schema Documentation
Complete ERD, relationships, and data flow
"""

# DATABASE SCHEMA - PHASE 3
# Target: PostgreSQL (production) / SQLite (development)
# ORM: SQLAlchemy 2.0+

## Table: users
```
users (
  id: INTEGER PRIMARY KEY
  username: VARCHAR(255) UNIQUE NOT NULL
  email: VARCHAR(255) UNIQUE NOT NULL
  full_name: VARCHAR(255)
  hashed_password: VARCHAR(255) NOT NULL
  role: ENUM(admin|user|viewer) DEFAULT 'user'
  is_active: BOOLEAN DEFAULT TRUE
  is_verified: BOOLEAN DEFAULT FALSE
  
  # Quotas
  api_calls_today: INTEGER DEFAULT 0
  api_quota_daily: INTEGER DEFAULT 1000
  storage_used_mb: FLOAT DEFAULT 0.0
  storage_quota_mb: FLOAT DEFAULT 500.0
  
  # Timestamps
  created_at: DATETIME DEFAULT NOW()
  updated_at: DATETIME DEFAULT NOW()
  last_login: DATETIME
  
  # Indexes
  INDEX idx_username(username)
  INDEX idx_email(email)
  INDEX idx_created_at(created_at)
)
```

## Table: api_keys
```
api_keys (
  id: INTEGER PRIMARY KEY
  user_id: INTEGER NOT NULL FOREIGN KEY(users.id)
  key_hash: VARCHAR(255) UNIQUE NOT NULL
  name: VARCHAR(255) NOT NULL
  last_used: DATETIME
  is_active: BOOLEAN DEFAULT TRUE
  created_at: DATETIME DEFAULT NOW()
  expires_at: DATETIME
  
  # Indexes
  INDEX idx_user_key(user_id, key_hash)
)
```

## Table: builds
```
builds (
  id: VARCHAR(36) PRIMARY KEY
  user_id: INTEGER NOT NULL FOREIGN KEY(users.id)
  
  # Project Info
  project_name: VARCHAR(255) NOT NULL
  description: TEXT
  requirements: TEXT NOT NULL
  tags: JSON DEFAULT []
  
  # Status
  status: ENUM(pending|running|completed|failed|cancelled) DEFAULT 'pending'
  
  # Execution
  started_at: DATETIME
  completed_at: DATETIME
  duration_seconds: FLOAT
  
  # Results
  generated_code: TEXT
  test_results: JSON
  build_logs: TEXT
  error_message: TEXT
  
  # Metadata
  celery_task_id: VARCHAR(255)
  created_at: DATETIME DEFAULT NOW()
  updated_at: DATETIME DEFAULT NOW()
  
  # Indexes
  INDEX idx_user_builds(user_id, created_at)
  INDEX idx_build_status(status, created_at)
  INDEX idx_celery_task(celery_task_id)
)
```

## Table: code_analysis
```
code_analysis (
  id: VARCHAR(36) PRIMARY KEY
  user_id: INTEGER NOT NULL FOREIGN KEY(users.id)
  build_id: VARCHAR(36) FOREIGN KEY(builds.id)
  
  # Input
  code_to_analyze: TEXT NOT NULL
  
  # Scores
  quality_score: FLOAT DEFAULT 0.0 (0-10)
  security_score: FLOAT DEFAULT 0.0 (0-10)
  maintainability_index: FLOAT DEFAULT 0.0
  coverage_percent: FLOAT DEFAULT 0.0
  
  # Issues
  security_issues: JSON DEFAULT []
  code_smells: JSON DEFAULT []
  type_errors: JSON DEFAULT []
  
  # Recommendations
  recommendations: JSON DEFAULT []
  suggested_refactorings: JSON DEFAULT []
  
  # Metrics
  lines_of_code: INTEGER DEFAULT 0
  cyclomatic_complexity: FLOAT DEFAULT 0.0
  
  # Timestamps
  created_at: DATETIME DEFAULT NOW()
  analysis_duration_ms: FLOAT
  
  # Indexes
  INDEX idx_user_analysis(user_id, created_at)
)
```

## Table: vector_memory
```
vector_memory (
  id: VARCHAR(36) PRIMARY KEY
  build_id: VARCHAR(36) FOREIGN KEY(builds.id)
  
  # Content
  content: TEXT NOT NULL
  content_type: VARCHAR(50) NOT NULL (code|documentation|test|analysis)
  
  # Metadata
  source_file: VARCHAR(255)
  language: VARCHAR(50) (python|javascript|typescript|etc)
  
  # Embedding
  embedding: JSON NOT NULL (768-dimensional vector)
  
  # Timestamps
  created_at: DATETIME DEFAULT NOW()
  
  # Indexes
  INDEX idx_build_memory(build_id)
  INDEX idx_content_type(content_type)
)
```

## Table: memory
```
memory (
  id: VARCHAR(36) PRIMARY KEY
  user_id: INTEGER NOT NULL FOREIGN KEY(users.id)
  
  # Memory Classification
  memory_type: VARCHAR(50) NOT NULL (conversation|preference|learning|context)
  
  # Content
  key: VARCHAR(255) NOT NULL
  value: JSON NOT NULL
  
  # Lifecycle
  created_at: DATETIME DEFAULT NOW()
  updated_at: DATETIME DEFAULT NOW()
  expires_at: DATETIME (NULL = permanent)
  
  # Importance
  importance: FLOAT DEFAULT 0.5 (0-1 for prioritization)
  
  # Indexes
  INDEX idx_user_memory(user_id, created_at)
  INDEX idx_memory_type(memory_type)
  INDEX idx_expiration(expires_at)
)
```

## Table: telegram_users
```
telegram_users (
  id: INTEGER PRIMARY KEY
  user_id: INTEGER NOT NULL FOREIGN KEY(users.id)
  telegram_id: INTEGER UNIQUE NOT NULL
  telegram_username: VARCHAR(255)
  chat_id: INTEGER NOT NULL
  
  # Status
  is_active: BOOLEAN DEFAULT TRUE
  conversation_state: VARCHAR(50) DEFAULT 'idle' (idle|awaiting_input|processing)
  
  # Timestamps
  created_at: DATETIME DEFAULT NOW()
  updated_at: DATETIME DEFAULT NOW()
  last_interaction: DATETIME
  
  # Indexes
  INDEX idx_telegram_id(telegram_id, unique)
  INDEX idx_user_id(user_id)
)
```

## Table: audit_logs
```
audit_logs (
  id: INTEGER PRIMARY KEY AUTO_INCREMENT
  user_id: INTEGER FOREIGN KEY(users.id)
  
  # Action
  action: VARCHAR(100) NOT NULL
  resource_type: VARCHAR(100) NOT NULL
  resource_id: VARCHAR(255)
  
  # Details
  details: JSON
  ip_address: VARCHAR(50)
  user_agent: VARCHAR(500)
  
  # Result
  success: BOOLEAN DEFAULT TRUE
  error_message: TEXT
  
  # Timestamps
  created_at: DATETIME DEFAULT NOW()
  
  # Indexes
  INDEX idx_user_audit(user_id, created_at)
  INDEX idx_action_time(action, created_at)
  INDEX idx_resource(resource_type, resource_id)
)
```

## Relationships

### One-to-Many
- User → Builds (1:N)
- User → CodeAnalysis (1:N)
- User → Memory (1:N)
- User → APIKey (1:N)
- User → AuditLog (1:N)
- User → TelegramUser (1:1)
- Build → CodeAnalysis (1:1)
- Build → VectorMemory (1:N)

### Foreign Key Constraints
```
User ←→ Builds (ON DELETE CASCADE)
User ←→ CodeAnalysis (ON DELETE CASCADE)
User ←→ Memory (ON DELETE CASCADE)
User ←→ APIKey (ON DELETE CASCADE)
User ←→ AuditLog (ON DELETE CASCADE)
Build ←→ CodeAnalysis (ON DELETE CASCADE)
Build ←→ VectorMemory (ON DELETE CASCADE)
```

## Indexes Strategy

### Performance Indexes
- users(username) - Fast user lookup
- users(email) - Email verification
- builds(user_id, created_at) - User build history
- builds(status, created_at) - Status filtering
- code_analysis(user_id, created_at) - Analysis history
- memory(user_id, created_at) - Memory retrieval
- memory(expires_at) - Cleanup query

### Search Indexes
- vector_memory(build_id) - Retrieval
- vector_memory(content_type) - Filtering
- telegram_users(telegram_id) - Quick lookup

## Data Types

### Mappings
- Enum types: Python enum + database ENUM
- JSON fields: Python dict/list → JSON storage
- Datetime: UTC timestamps
- Secrets: Never stored plaintext

## Query Patterns

### Common Queries
```sql
-- Get user builds with status
SELECT * FROM builds 
WHERE user_id = ? AND created_at > ? 
ORDER BY created_at DESC 
LIMIT 20;

-- Find similar code (pre-vector)
SELECT * FROM vector_memory 
WHERE build_id = ? AND content_type = 'code'
ORDER BY created_at DESC;

-- User activity audit
SELECT * FROM audit_logs 
WHERE user_id = ? 
ORDER BY created_at DESC 
LIMIT 100;

-- Memory retrieval by type
SELECT * FROM memory 
WHERE user_id = ? AND memory_type = ? 
ORDER BY importance DESC;
```

## Capacity Planning

### Storage Estimates
- User: ~1 KB
- Build: ~50 KB (with code)
- CodeAnalysis: ~10 KB
- VectorMemory: ~3 KB (768-dim embedding as JSON)
- Memory: ~2 KB

### For 10,000 users, 1000 builds each:
- Users: 10 MB
- Builds: 500 GB
- Analyses: 100 GB
- Vectors: 30 GB
- Audit Logs: 10 GB
- **Total: ~650 GB** (justifies vector DB separation)

## Migration Strategy (Phase 4)

### Alembic Migrations
```python
# Example migration
def upgrade():
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(255), nullable=False),
        ...
    )

def downgrade():
    op.drop_table('users')
```

### Backwards Compatibility
- Never remove columns, mark as deprecated
- Always add new columns with defaults
- Test migrations in staging first

## Performance Tuning

### Connection Pooling
```python
# SQLAlchemy
pool_size=20  # Connections
max_overflow=10  # Additional connections
pool_pre_ping=True  # Test before use
```

### Query Optimization
- Use indexes on filtered columns
- Batch inserts for bulk operations
- Use select() for large result sets
- Consider pagination (LIMIT/OFFSET)

## Backup Strategy

### PostgreSQL
```bash
# Daily backup
pg_dump -U user -d agent_db > backup.sql

# Restore
psql -U user -d agent_db < backup.sql
```

### Chroma (Vector DB)
```bash
# Auto-saved to disk
cp -r data/chroma data/chroma.backup
```

---

**Schema Version**: 3.0.0
**Last Updated**: Phase 3 Implementation
**Next Review**: Phase 4 (Alembic migrations)
