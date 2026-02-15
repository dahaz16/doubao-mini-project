# Stn LLM 改造调研报告 v3 (Remove Shot / No Stage Time)

## 1. 改造背景
用户希望简化 `Stn LLM` (速记员) 的结构化提取逻辑：
- **移除** "Shot" (镜头) 实体 - 不再提取、不再入库、不再写入 Storyboard
- **保留** "Character" (人物) 实体 - 但 `related_shot_id` 将永久为 NULL
- **移除** "Stage" (人生阶段) 的起止时间 - `stage_start_time` 和 `stage_end_time` 永久为 NULL
- **保留** "Stage" 和 "Topic" 实体 - 作为核心两层结构

**改造策略：**
- 通过丰富 `Topic.content` 和 `Topic.summary` 来弥补 Shot 层缺失的细节
- 采用**暴力清理**方案：清空 `shot` 和 `character` 表的历史数据
- 修改后端代码，完全移除 Shot 处理逻辑
- 更新 Stn LLM 提示词，移除 Shot 和 Stage 时间相关指令

---

## 2. 全局代码影响分析 (Global Impact Analysis)

### 2.1 Character (人物) 的关联性变化 ✅
- **现状：** 数据库中 `character` 表有外键 `related_shot_id`，用于将人物挂载到 Shot 下
- **改造后：** 所有新生成的 Character 的 `related_shot_id` 将永久为 `NULL`
- **业务影响：** 
  - Character 成为独立实体，不再关联具体事件
  - 可以看到"出现过这个人物"，但无法通过数据库查询"这个人物在哪个 Topic 中出现"
- **用户决策：** 接受此状态，通过丰富 `Topic.content` 来弥补人物上下文信息的缺失

### 2.2 数据流变化 ✅
- **LLM 输出结构：** S (Stage) -> T (Topic) + C (Character)
  - 关系 R 仅包含 T->S (Topic 指向 Stage)
  - Character 不再有层级关系
- **Storyboard 变化：** 
  - 保留：Type 1 (S), Type 2 (T), Type 4 (C)
  - 移除：Type 3 (O/Shot) 将完全消失
- **下游 Agent 影响：**
  - **Dir Agent：** 通过 Storyboard 获取故事大纲，不受影响（用户会丰富 Topic.summary）
  - **Wtr Agent：** 通过 Topic 生成回忆录，不受影响（用户会丰富 Topic.content）

### 2.3 历史数据处理方案 ✅
- **策略：** 暴力清理，清空 `shot` 和 `character` 表的所有历史数据
- **原因：** 当前数据库无重要数据，避免新老数据混合导致的逻辑混乱
- **执行方式：** 在代码修改前，执行 SQL 清理脚本

### 2.4 Stage 时间字段处理 ✅
- **策略：** `stage_start_time` 和 `stage_end_time` 永久设为 `NULL`
- **实现方式：**
  - 后端代码：`insert_stage` 和 `update_stage` 函数强制传入 `None`
  - Prompt 层面：移除 Stage 时间提取的相关指令
- **用户决策：** 当前数据库无重要时间信息，接受暴力清理

---

## 3. 需要修改的代码位置 (Code Changes)

### 3.1 `backend/stn_service.py` - 核心逻辑修改

**文件路径：** `backend/stn_service.py`

#### 修改 1: `_process_parsed_data` 函数 (第 339-395 行)
**操作：** 完全注释掉 Shot 处理循环
```python
# 3. 处理 Shot (O) - ❌ v3.0: 已移除 Shot 实体
# shots = data.get('O', [])
# for shot in shots:
#     shot_id = _process_shot(user_id, shot, id_map)
#     if shot_id:
#         story_id = _create_storyboard_entry(user_id, 'O', shot_id, shot)
#         if story_id:
#             max_story_id = story_id
```

#### 修改 2: `_process_stage` 函数 (第 398-428 行)
**操作：** 强制 `start_time` 和 `end_time` 为 `None`
```python
# 新建时
stage_id = insert_stage(
    user_id=user_id,
    title=stage.get('title', ''),
    summary=stage.get('summary'),
    content=stage.get('content'),
    start_time=None,  # ✅ v3.0: 强制为 None
    end_time=None     # ✅ v3.0: 强制为 None
)
```

#### 修改 3: `_process_character` 函数 (第 533-562 行)
**操作：** 确认 `related_shot_id` 已经是 `None`（当前代码已正确，无需修改）
```python
# 当前代码第 545 行已经是 None，保持不变
char_id = insert_character(
    user_id=user_id,
    name=char.get('name', ''),
    relation=char.get('relation'),
    evaluation=char.get('evaluation'),
    related_shot_id=None  # ✅ 已正确
)
```

#### 修改 4: `_process_relation` 函数 (第 565-606 行)
**操作：** 添加防御性代码，忽略涉及 Shot (O) 的关系
```python
def _process_relation(user_id: str, rel: Dict[str, Any], id_map: Dict[str, int]):
    # ✅ v3.0: 防御性检查 - 忽略涉及 Shot 的关系
    src_type = _get_entity_type_from_id(rel.get('src'), id_map)
    tgt_type = _get_entity_type_from_id(rel.get('tgt'), id_map)
    
    if src_type == 'O' or tgt_type == 'O':
        logging.warning(f"⚠️ v3.0: 忽略涉及 Shot 的关系 - src={rel.get('src')}, tgt={rel.get('tgt')}")
        return
    
    # ... 原有逻辑
```

#### 修改 5: `_create_storyboard_entry` 函数 (第 651-668 行)
**操作：** Character 的 Storyboard 格式保持不变（当前已正确）
- 当前格式：`[C:{character_id}] {Name} | {Relation}`
- 不需要修改，因为 Character 不再有父级关联

### 3.2 `backend/stn_database.py` - 数据库操作函数

**文件路径：** `backend/stn_database.py`

#### 修改 6: `insert_stage` 函数
**操作：** 确认函数签名支持 `start_time=None` 和 `end_time=None`（需检查当前实现）

#### 修改 7: `update_stage` 函数
**操作：** 确认更新时不会覆盖时间字段为非 NULL 值

### 3.3 Stn LLM 提示词修改 (稍后执行)

**时机：** 在代码修改完成并测试通过后，再更新 Prompt

**修改要点：**
1. **移除 Shot (O) 的所有定义和示例**
   - 删除 "实体提取层级" 中的 Shot 说明
   - 删除输出格式中的 `"O": []` 字段
   - 删除所有涉及 Shot 的关系示例（如 `O->T`, `C->O`）

2. **移除 Stage 时间提取指令**
   - 删除 `start_time` 和 `end_time` 字段的说明
   - 在 Stage 示例中不再包含时间字段

3. **强化 Topic 内容丰富度要求**
   - 将 `Topic.content` 字数要求从 "20-100字" 提升到 "50-200字"
   - 将 `Topic.summary` 字数要求从 "10-30字" 提升到 "20-50字"
   - 明确要求 Topic 需包含足够的细节描述

4. **更新输出格式示例**
```json
{
  "type": "memory",
  "memory_content": {
    "S": [{"pt": "n", "tid": "s1", "title": "童年时光", "summary": "...", "content": "..."}],
    "T": [{"pt": "n", "tid": "t1", "title": "外婆家的小院", "summary": "...", "content": "..."}],
    "C": [{"pt": "n", "tid": "c1", "name": "外婆", "relation": "祖孙", "evaluation": "..."}],
    "R": [{"type": "link", "src": "t1", "tgt": "s1"}]
  }
}
```

**注意：** Prompt 修改将在实施计划的最后阶段执行，确保代码层面已完全适配

## 4. 验证计划 (Verification Plan)

### 4.1 数据库清理验证
**执行方式：** 手动执行 SQL 脚本
```sql
-- 检查清理前的数据量
SELECT COUNT(*) FROM shot;
SELECT COUNT(*) FROM character;

-- 执行清理
DELETE FROM character;
DELETE FROM shot;

-- 确认清理结果
SELECT COUNT(*) FROM shot;      -- 应返回 0
SELECT COUNT(*) FROM character; -- 应返回 0
```

### 4.2 单元测试 - Character 入库验证
**测试目标：** 确认 Character 可以成功入库，且 `related_shot_id` 为 NULL

**测试方式：** 创建测试脚本 `test_stn_character_null.py`
```python
# 模拟 Stn LLM 输出（不包含 Shot）
# 调用 _process_character
# 查询数据库验证 related_shot_id = NULL
```

### 4.3 单元测试 - Stage 时间字段验证
**测试目标：** 确认 Stage 的 `start_time` 和 `end_time` 为 NULL

**测试方式：** 创建测试脚本 `test_stn_stage_no_time.py`
```python
# 模拟 Stn LLM 输出（Stage 不包含时间）
# 调用 _process_stage
# 查询数据库验证 start_time = NULL, end_time = NULL
```

### 4.4 集成测试 - 完整 Stn Agent 流程
**测试目标：** 端到端验证 Stn Agent 不再处理 Shot

**测试方式：** 使用现有测试脚本 `verify_stn_logic.py`（需修改）
- 模拟用户对话输入
- 触发 Stn Agent
- 验证：
  - `shot` 表无新增记录
  - `character` 表有新增记录，且 `related_shot_id = NULL`
  - `storyboard` 表无 Type 3 记录
  - `stage` 表的 `start_time` 和 `end_time` 为 NULL

### 4.5 回归测试 - Dir Agent 和 Wtr Agent
**测试目标：** 确认下游 Agent 不受影响

**测试方式：** 手动测试
1. 触发 Stn Agent 生成新的 Storyboard（无 Shot）
2. 触发 Dir Agent，检查生成的 Hint 是否正常
3. 积累足够 Topic 后，触发 Wtr Agent，检查生成的回忆录质量

**预期结果：**
- Dir Agent 能正常生成采访引导问题
- Wtr Agent 能正常生成回忆录文章（依赖用户丰富 Topic 内容）
