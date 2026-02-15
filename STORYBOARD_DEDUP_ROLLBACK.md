# Storyboard 去重改造 - 回滚指南

## 改造内容

**文件**: `backend/stn_database.py`  
**函数**: `insert_storyboard` (第 315-371 行)  
**改造日期**: 2024-02-14  
**改造方案**: 方案 A（保守改造）

## 改造效果

### 改造前
- 每次 Stn LLM 更新实体时，都会在 storyboard 中新增一条记录
- 导致大量重复数据（如 Topic #87 重复 17 次）

### 改造后
- 写入新记录前，删除相同 `entity_id` 的已处理旧记录
- 只删除 `stn_processed_status=1 AND dir_processed_status=1` 的记录
- 保留待处理记录，避免数据丢失

## 测试结果

运行 `python3 test_storyboard_dedup.py` 的测试结果：

```
删除前记录数: 17
删除后记录数: 2
减少记录数: 15

待处理记录（删除前）: 1
待处理记录（删除后）: 2  # 包含新插入的记录
✅ 待处理记录已正确保留
```

## 如何回滚

### 方法 1：注释掉去重代码（推荐）

打开 `backend/stn_database.py`，找到第 338-350 行，注释掉以下代码：

```python
# ============================================================
# 🔧 v2024-02-14 新增：去重逻辑（方案 A - 保守改造）
# ============================================================
# 删除相同 entity_id 的已处理旧记录，避免 storyboard 重复数据
# 只删除已被 Stn 和 Dir 都处理过的记录（status=1），保留待处理记录
# 
# ⚠️ 如需回滚：注释掉下面 6 行代码即可恢复旧逻辑
# ============================================================
# cursor.execute("""
#     DELETE FROM storyboard
#     WHERE user_id = %s 
#       AND entity_id = %s 
#       AND story_type = %s
#       AND stn_processed_status = 1 
#       AND dir_processed_status = 1
# """, (user_id, entity_id, story_type))
# deleted_count = cursor.rowcount
# if deleted_count > 0:
#     logging.info(f"🗑️  Storyboard 去重: 删除 {deleted_count} 条已处理旧记录 (entity_id={entity_id}, type={story_type})")
# ============================================================
# 🔧 去重逻辑结束
# ============================================================
```

### 方法 2：恢复原始代码

将 `insert_storyboard` 函数替换为以下代码：

```python
def insert_storyboard(
    user_id: str,
    story_type: int,
    entity_id: int,
    story_content: str
) -> Optional[int]:
    """
    插入故事板记录
    
    story_type: 1=Stage, 2=Topic, 3=Shot, 4=Character
    stn_processed_status 默认为 0（新记录，待 Stn 下次使用）
    dir_processed_status 默认为 0（待 Dir 处理）
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO storyboard (user_id, story_type, entity_id, story_content)
                    VALUES (%s, %s, %s, %s)
                    RETURNING story_id
                """, (user_id, story_type, entity_id, story_content))
                story_id = cursor.fetchone()[0]
                conn.commit()
                logging.info(f"✅ Storyboard 插入: story_id={story_id}, type={story_type}, entity={entity_id}")
                return story_id
    except Exception as e:
        logging.error(f"❌ Storyboard 插入失败: {e}")
        return None
```

## 重启后端服务

回滚后需要重启后端服务：

```bash
# 查找后端进程
ps aux | grep python | grep backend

# 杀死进程（替换 <PID> 为实际进程 ID）
kill <PID>

# 重新启动
cd /Users/wangyituo/Documents/拓的文稿/项目/回忆录项目/回忆录代码项目/doubao-mini-project
./run_backend.sh
```

## 验证回滚

运行测试脚本验证：

```bash
python3 test_storyboard_dedup.py
```

如果看到 "删除了 0 条已处理的旧记录"，说明回滚成功。

## 监控指标

### 正常运行时应观察的指标

1. **日志中的去重信息**：
   ```
   🗑️  Storyboard 去重: 删除 X 条已处理旧记录 (entity_id=XX, type=X)
   ```

2. **重复数据数量**：
   ```sql
   SELECT entity_id, story_type, COUNT(*) as count
   FROM storyboard
   GROUP BY entity_id, story_type
   HAVING COUNT(*) > 1
   ORDER BY count DESC;
   ```
   
   改造后，重复数量应该逐渐减少。

3. **待处理记录数量**：
   ```sql
   SELECT COUNT(*) FROM storyboard 
   WHERE stn_processed_status = 0 OR dir_processed_status = 0;
   ```
   
   应该保持稳定，不应该异常减少。

## 潜在问题及解决方案

### 问题 1：Dir Agent 读取到不完整数据

**症状**：Dir LLM 生成的提示词质量下降

**原因**：并发删除时，Dir Agent 正在读取

**解决**：回滚改造，等待并发控制优化后再实施

### 问题 2：待处理记录丢失

**症状**：`stn_processed_status=0` 的记录数量异常减少

**原因**：删除逻辑有误，误删了待处理记录

**解决**：立即回滚，检查代码逻辑

### 问题 3：性能下降

**症状**：Stn Agent 处理速度明显变慢

**原因**：DELETE 操作耗时过长

**解决**：检查数据库索引，或回滚改造

## 联系方式

如有问题，请查看：
- 调研报告：`stn_storyboard_analysis.md`
- 测试脚本：`test_storyboard_dedup.py`
- 代码文件：`backend/stn_database.py`
