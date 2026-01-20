# Improvement Ideas: POC Roadmap

## Vision

Transform the current single-request system into a working POC that supports:
- **Conversational chat interface** with multi-turn dialogues
- **File and photo uploads** for agent analysis
- **Database connections** for schema-aware agent operations
- **Session-based architecture** with persistent state
- **Agent lifecycle management** tied to chat sessions

## Core POC Requirements

### 1. Conversational Chat Interface

**Current State**: Single text area with one-shot request-response

**Target State**: ChatGPT-like conversational interface

**Implementation Details**:
- Replace text area with chat message container
- Display message history with user/assistant roles
- Input area at bottom with send button
- Scrollable message history
- Support for multi-turn conversations
- Maintain full conversation context across messages

**Technical Approach**:
- Use Streamlit's `chat_message` component for message display
- Store messages in session state
- Pass full conversation history to agents
- Update UI to show streaming or progressive responses

**Benefits**:
- Natural interaction pattern
- Context preservation across turns
- Better user experience
- Enables iterative refinement

### 2. File Upload Capability

**Current State**: No file handling

**Target State**: Upload, store, and analyze files

**Implementation Details**:
- Add `st.file_uploader` widget in sidebar
- Support multiple file types:
  - Text files (.txt, .md, .py, etc.)
  - PDFs (.pdf)
  - CSV files (.csv)
  - JSON files (.json)
  - Office documents (.docx, .xlsx) - optional
- Store uploaded files in `uploads/{session_id}/` directory
- Create file metadata in session data
- Extract text content from files
- Pass file content to agents as context

**New Tools to Create**:
- `FileReadTool`: Read content from uploaded files
- `FileListTool`: List files in current session
- `FileAnalyzeTool`: Analyze file content (summarize, extract key info)

**File Processing**:
- Text files: Direct read
- PDFs: Use `pypdf` or `pdfplumber` for text extraction
- CSVs: Use `pandas` for data analysis
- JSON: Parse and structure for agents

**Integration**:
- Files uploaded in sidebar
- File list shown in sidebar
- Agent prompts include: "You have access to the following files: [list]"
- Agents can request file content via tools

### 3. Photo/Image Upload Capability

**Current State**: No image processing

**Target State**: Upload and analyze images with vision models

**Implementation Details**:
- Add `st.file_uploader` for images (with accept parameter)
- Support formats: PNG, JPG, JPEG, GIF, WebP
- Store images in `uploads/{session_id}/images/`
- Create image analysis tools
- Integrate with vision-capable models (OpenAI GPT-4 Vision, etc.)

**New Tools to Create**:
- `ImageAnalysisTool`: Analyze images with vision models
- `ImageDescribeTool`: Generate descriptions of images
- `ImageExtractTextTool`: OCR for text extraction (optional)

**Technical Approach**:
- Base64 encode images for API transmission
- Use OpenAI vision API or similar
- Store image metadata (filename, size, format) in session
- Pass image references to agents

**Integration**:
- Images uploaded in sidebar
- Image gallery in sidebar
- Agents can analyze images when mentioned
- Vision context included in agent prompts

### 4. Database Connection Feature

**Current State**: No database capabilities

**Target State**: Connect to databases and use schema context

**Implementation Details**:
- Add database connection panel in sidebar
- Support multiple database types:
  - PostgreSQL
  - MySQL
  - SQLite
- Connection string input (with masking for security)
- Test connection button
- Schema/table selector
- Store connection info in session (encrypted or masked)

**New Tools to Create**:
- `DatabaseConnectionTool`: Manage DB connections
- `SchemaIntrospectionTool`: Fetch table/schema metadata
  - List tables in database
  - Get table schemas (columns, types, constraints)
  - Get foreign key relationships
- `DatabaseQueryTool`: Execute queries with safety checks
  - Query validation (prevent DROP, DELETE without WHERE, etc.)
  - Result limiting (max rows)
  - Read-only mode option
  - Query result formatting

**Technical Approach**:
- Use SQLAlchemy for database abstraction
- Connection pooling per session
- Schema introspection via SQLAlchemy metadata
- Query execution with transaction management
- Safety checks: whitelist allowed operations

**Integration**:
- Connection UI in sidebar
- Selected tables shown in sidebar
- Agent prompts include: "You have access to the following database tables: [schema]"
- Agents can query databases via tools
- Query results passed as context

**Safety Considerations**:
- Query validation before execution
- Read-only mode by default
- Row limits on queries
- No DDL operations (CREATE, DROP, ALTER)
- No DML operations without explicit user approval

### 5. Session Management with Local File Storage

**Current State**: No session persistence

**Target State**: Session-based architecture with file storage

**Implementation Details**:
- Create `runtime_agents/session.py` module
- Session data structure:
  ```python
  {
    "session_id": str,
    "created_at": datetime,
    "last_accessed": datetime,
    "chat_history": List[Message],
    "files": List[FileMetadata],
    "images": List[ImageMetadata],
    "db_connections": List[DBConnection],
    "agent_state": Dict,
    "agent_results": List[AgentResult]
  }
  ```
- Store sessions in `sessions/{session_id}.json`
- Session file format: JSON for portability
- Session manager for CRUD operations
- Auto-cleanup of old sessions (configurable retention)

**Session Lifecycle**:
1. User creates new session (or selects existing)
2. Session loaded into Streamlit session state
3. All interactions update session
4. Session saved after each interaction
5. Session cleanup when user ends/closes session

**File Structure**:
```
sessions/
  {session_id_1}.json
  {session_id_2}.json
  ...

uploads/
  {session_id_1}/
    file1.pdf
    file2.csv
    images/
      image1.png
  {session_id_2}/
    ...
```

**Benefits**:
- Portable (no database required)
- Easy to backup/restore
- Session isolation
- Can resume conversations

### 6. Agent Lifecycle Management

**Current State**: Agents created per request, no persistence

**Target State**: Agents persist for session duration

**Implementation Details**:
- Agents created when session starts (or on first use)
- Agent instances stored in session
- Agent state saved to session file
- Conversation history maintained per agent
- Agent cleanup on session end

**Agent State**:
- Conversation history with user
- Tool call history
- Context from files/database/images
- Internal state (if any)

**Multi-turn Support**:
- Agents remember previous interactions in session
- Context accumulates across turns
- Agents can reference earlier parts of conversation

**Technical Changes**:
- Modify `AgentInstance` to support conversation history
- Update `Orchestrator` to maintain agent instances per session
- Store agent state in session data
- Load agent state when session resumes

### 7. Enhanced Tool Execution

**Current State**: Tools described but not executed

**Target State**: Automatic tool call parsing and execution

**Implementation Details**:
- Parse tool calls from agent responses
- Support OpenAI function calling format
- Execute tools and feed results back to agents
- Support multi-step tool execution loops
- Tool result formatting for agents

**Tool Call Format**:
- JSON-based tool calls
- Function name and parameters
- Result passed back to agent
- Agent can make multiple tool calls

**Execution Loop**:
1. Agent generates response with tool calls
2. System parses tool calls
3. Execute tools
4. Feed results back to agent
5. Agent generates final response
6. Repeat if needed (with iteration limits)

**Safety**:
- Tool execution limits
- Timeout per tool
- Error handling and reporting
- Sandboxing for dangerous operations

## Implementation Priorities

### Phase 1: Foundation (High Priority)
1. **Session Management**
   - Create session module
   - Implement session storage
   - Session CRUD operations
   - Session cleanup

2. **Conversational Chat Interface**
   - Replace UI with chat interface
   - Message history display
   - Session integration
   - Context preservation

### Phase 2: File Handling (High Priority)
3. **File Upload and Processing**
   - File uploader widget
   - File storage system
   - Text extraction tools
   - File analysis tools
   - Agent integration

### Phase 3: Database Integration (Medium Priority)
4. **Database Connection**
   - Connection UI
   - SQLAlchemy integration
   - Schema introspection
   - Query execution tools
   - Safety checks

### Phase 4: Advanced Features (Medium Priority)
5. **Photo Upload and Vision**
   - Image uploader
   - Vision API integration
   - Image analysis tools
   - Agent integration

6. **Enhanced Tool Execution**
   - Tool call parsing
   - Execution loop
   - Result formatting
   - Error handling

### Phase 5: Polish (Low Priority)
7. **Agent Lifecycle Improvements**
   - Agent state persistence
   - Multi-turn context
   - Agent memory
   - Performance optimization

## Technical Architecture Changes

### New Modules

1. **`runtime_agents/session.py`**
   - `Session` dataclass
   - `SessionManager` class
   - Session file I/O
   - Session validation

2. **`runtime_agents/db_tools.py`**
   - Database connection management
   - Schema introspection
   - Query execution
   - Safety validators

3. **`runtime_agents/image_tools.py`**
   - Image processing
   - Vision API integration
   - Image analysis

### Modified Modules

1. **`app.py`**
   - Complete UI overhaul
   - Chat interface
   - File/image uploaders
   - Database connection UI
   - Session management UI

2. **`runtime_agents/tools.py`**
   - Add file processing tools
   - Extend tool protocol if needed

3. **`runtime_agents/agents.py`**
   - Add conversation history support
   - State persistence methods

4. **`runtime_agents/orchestrator.py`**
   - Session-aware agent management
   - Multi-turn conversation support
   - Context from files/DB/images

## Dependencies to Add

```toml
dependencies = [
  # Existing...
  "sqlalchemy>=2.0.0",      # Database abstraction
  "pypdf>=3.0.0",           # PDF text extraction
  "Pillow>=10.0.0",         # Image processing
  "pandas>=2.0.0",          # CSV/data processing
  "python-dotenv>=1.0.0",   # Already added
]
```

## File Structure Changes

```
runtime-agents/
  docs/
    understanding.md          # NEW
    improvement_ideas.md     # NEW
  sessions/                   # NEW - session storage
    {session_id}.json
  uploads/                    # NEW - file storage
    {session_id}/
      files/
      images/
  runtime_agents/
    session.py                # NEW
    db_tools.py               # NEW
    image_tools.py            # NEW
    # ... existing files (modified)
```

## Security Considerations

1. **File Uploads**
   - File size limits
   - File type validation
   - Virus scanning (optional)
   - Secure file storage

2. **Database Connections**
   - Connection string encryption
   - Query validation
   - Read-only mode by default
   - Access control

3. **Session Data**
   - Sensitive data masking
   - Session isolation
   - Secure file storage
   - Cleanup of old sessions

4. **Tool Execution**
   - Sandboxing
   - Timeout limits
   - Resource limits
   - Error handling

## Success Metrics

- Users can have multi-turn conversations
- Files can be uploaded and analyzed
- Images can be processed
- Databases can be connected and queried
- Sessions persist across app restarts
- Agents maintain context across turns
- Tool calls are executed automatically

## Future Enhancements (Post-POC)

- Agent template management UI
- Custom agent creation
- Agent versioning
- MCP tool integration
- Parallel agent execution
- Agent collaboration patterns
- Performance monitoring
- Cost tracking
- User authentication
- Multi-user support
