-- TESS Initial Database Schema
-- PostgreSQL migration for conversation memory storage

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Conversations table
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id VARCHAR(255) UNIQUE NOT NULL,
    user_identifier VARCHAR(255),  -- email, phone, or anonymous_id
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb,
    CONSTRAINT session_id_not_empty CHECK (session_id <> '')
);

-- Index for faster lookups by session_id and user_identifier
CREATE INDEX idx_conversations_session_id ON conversations(session_id);
CREATE INDEX idx_conversations_user_identifier ON conversations(user_identifier);
CREATE INDEX idx_conversations_created_at ON conversations(created_at);

-- Messages table
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL,  -- 'user', 'assistant', 'system'
    content TEXT NOT NULL,
    tool_calls JSONB,  -- Store tool invocations
    timestamp TIMESTAMP DEFAULT NOW(),
    tokens_used INTEGER,
    CONSTRAINT role_valid CHECK (role IN ('user', 'assistant', 'system'))
);

-- Index for efficient message retrieval
CREATE INDEX idx_messages_conversation_timestamp ON messages(conversation_id, timestamp);
CREATE INDEX idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX idx_messages_timestamp ON messages(timestamp);

-- Conversation summaries table
CREATE TABLE IF NOT EXISTS conversation_summaries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    summary TEXT NOT NULL,
    message_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Index for summaries
CREATE INDEX idx_summaries_conversation_id ON conversation_summaries(conversation_id);
CREATE INDEX idx_summaries_created_at ON conversation_summaries(created_at);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to auto-update updated_at
CREATE TRIGGER update_conversations_updated_at
    BEFORE UPDATE ON conversations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Function to archive old conversations
CREATE OR REPLACE FUNCTION archive_old_conversations(days_old INTEGER DEFAULT 90)
RETURNS INTEGER AS $$
DECLARE
    archived_count INTEGER;
BEGIN
    -- Create archive table if it doesn't exist
    CREATE TABLE IF NOT EXISTS archived_conversations (LIKE conversations INCLUDING ALL);
    CREATE TABLE IF NOT EXISTS archived_messages (LIKE messages INCLUDING ALL);

    -- Move old conversations to archive
    WITH archived AS (
        DELETE FROM conversations
        WHERE created_at < NOW() - INTERVAL '1 day' * days_old
        RETURNING *
    )
    INSERT INTO archived_conversations
    SELECT * FROM archived;

    GET DIAGNOSTICS archived_count = ROW_COUNT;

    RETURN archived_count;
END;
$$ LANGUAGE plpgsql;

-- Create a view for recent conversations with message counts
CREATE OR REPLACE VIEW conversation_stats AS
SELECT
    c.id,
    c.session_id,
    c.user_identifier,
    c.created_at,
    c.updated_at,
    COUNT(m.id) as message_count,
    MAX(m.timestamp) as last_message_at,
    SUM(COALESCE(m.tokens_used, 0)) as total_tokens
FROM conversations c
LEFT JOIN messages m ON c.id = m.conversation_id
GROUP BY c.id, c.session_id, c.user_identifier, c.created_at, c.updated_at;

-- Comments for documentation
COMMENT ON TABLE conversations IS 'Stores conversation sessions and metadata';
COMMENT ON TABLE messages IS 'Stores individual messages within conversations';
COMMENT ON TABLE conversation_summaries IS 'Stores summaries of long conversations';
COMMENT ON COLUMN conversations.session_id IS 'Unique session identifier for the conversation';
COMMENT ON COLUMN conversations.user_identifier IS 'User email, phone, or anonymous ID';
COMMENT ON COLUMN conversations.metadata IS 'Additional conversation context and preferences';
COMMENT ON COLUMN messages.role IS 'Message role: user, assistant, or system';
COMMENT ON COLUMN messages.tool_calls IS 'JSON array of tool invocations made by the agent';
COMMENT ON COLUMN messages.tokens_used IS 'Number of tokens used for this message';

-- Insert initial system message template (optional)
-- This can be used to track system prompts
INSERT INTO conversations (session_id, user_identifier, metadata)
VALUES ('system', 'system', '{"type": "system_template"}')
ON CONFLICT (session_id) DO NOTHING;
