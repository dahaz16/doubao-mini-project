-- ============================================================================
-- 创建 prompt_config 表（提示词配置表）
-- v3.4 新增表
-- ============================================================================

CREATE TABLE IF NOT EXISTS prompt_config (
    prompt_id BIGSERIAL PRIMARY KEY,
    llm_type SMALLINT NOT NULL,  -- 0:Intv, 1:Stn, 2:Dir
    prompt_content TEXT,
    remark VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引加速查询
CREATE INDEX IF NOT EXISTS idx_prompt_config_llm_type ON prompt_config(llm_type);
CREATE INDEX IF NOT EXISTS idx_prompt_config_active ON prompt_config(is_active);

-- 添加注释
COMMENT ON TABLE prompt_config IS '提示词配置表，支持动态管理各 LLM 的 System Prompt';
COMMENT ON COLUMN prompt_config.llm_type IS 'LLM 类型：0=intv, 1=stn, 2=dir';
COMMENT ON COLUMN prompt_config.prompt_content IS 'System Prompt 内容';
COMMENT ON COLUMN prompt_config.is_active IS '是否启用，方便快速回滚版本';
