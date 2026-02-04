# -*- coding: utf-8 -*-
"""
配置管理模块
提供系统配置和模型配置的读取功能，支持缓存机制
"""

from typing import Optional, Dict, Any
from .database import get_db_connection
import logging
from functools import lru_cache

class ConfigManager:
    """配置管理器"""
    
    def __init__(self):
        self._config_cache = {}
        self._model_cache = {}
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """
        获取系统配置值
        
        Args:
            key: 配置键名
            default: 默认值（如果配置不存在）
        
        Returns:
            配置值（自动转换类型）
        """
        # 先从缓存读取
        if key in self._config_cache:
            return self._config_cache[key]
        
        # 从数据库读取
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT config_value, config_type 
                    FROM sys_config 
                    WHERE config_key = %s
                """, (key,))
                result = cursor.fetchone()
                
                if not result:
                    logging.warning(f"配置项 {key} 不存在，使用默认值: {default}")
                    return default
                
                value, config_type = result
                
                # 类型转换
                converted_value = self._convert_value(value, config_type)
                
                # 缓存
                self._config_cache[key] = converted_value
                
                return converted_value
    
    def get_model_config(self, model_id: int) -> Optional[Dict[str, Any]]:
        """
        获取模型配置
        
        Args:
            model_id: 模型 ID
        
        Returns:
            模型配置字典
        """
        # 先从缓存读取
        if model_id in self._model_cache:
            return self._model_cache[model_id]
        
        # 从数据库读取
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT model_id, model_name_cn, model_name_en, model_type, 
                           api_model_id, input_price, output_price, 
                           cache_discount, cache_storage_price, cluster_id, remark
                    FROM base_models 
                    WHERE model_id = %s
                """, (model_id,))
                result = cursor.fetchone()
                
                if not result:
                    logging.warning(f"模型 ID {model_id} 不存在")
                    return None
                
                model_config = {
                    'model_id': result[0],
                    'model_name_cn': result[1],
                    'model_name_en': result[2],
                    'model_type': result[3],
                    'api_model_id': result[4],
                    'input_price': float(result[5]) if result[5] else 0,
                    'output_price': float(result[6]) if result[6] else 0,
                    'cache_discount': float(result[7]) if result[7] else 0.5,
                    'cache_storage_price': float(result[8]) if result[8] else 0,
                    'cluster_id': result[9],
                    'remark': result[10]
                }
                
                # 缓存
                self._model_cache[model_id] = model_config
                
                return model_config
    
    def get_model_by_config_key(self, config_key: str) -> Optional[Dict[str, Any]]:
        """
        通过配置键获取模型配置
        
        Args:
            config_key: 配置键名（如 'intv_llm_model'）
        
        Returns:
            模型配置字典
        """
        model_id = self.get_config(config_key)
        if model_id is None:
            return None
        
        return self.get_model_config(int(model_id))
    
    def get_active_prompt(self, llm_type: int) -> Optional[str]:
        """
        获取指定 LLM 类型的最新 active prompt
        
        Args:
            llm_type: LLM 类型 (0:Intv, 1:Stn, 2:Dir)
        
        Returns:
            prompt_content 字符串，若不存在则返回 None
        """
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT prompt_content
                    FROM prompt_config
                    WHERE llm_type = %s AND is_active = TRUE
                    ORDER BY prompt_id DESC
                    LIMIT 1
                """, (llm_type,))
                result = cursor.fetchone()
                
                if not result:
                    logging.warning(f"未找到 llm_type={llm_type} 的 active prompt")
                    return None
                
                return result[0]
    
    def clear_cache(self):
        """清空缓存"""
        self._config_cache.clear()
        self._model_cache.clear()
        logging.info("配置缓存已清空")
    
    def _convert_value(self, value: str, config_type: str) -> Any:
        """
        根据配置类型转换值
        
        Args:
            value: 配置值（字符串）
            config_type: 配置类型
        
        Returns:
            转换后的值
        """
        if config_type == 'number':
            # 尝试转换为整数，失败则转为浮点数
            try:
                if '.' in value:
                    return float(value)
                else:
                    return int(value)
            except ValueError:
                logging.warning(f"无法将 {value} 转换为数字，返回字符串")
                return value
        
        elif config_type == 'select':
            # select 类型通常是 ID，转为整数
            try:
                return int(value)
            except ValueError:
                return value
        
        else:  # text 或其他
            return value


# 全局配置管理器实例
config_manager = ConfigManager()


# 便捷函数
def get_config(key: str, default: Any = None) -> Any:
    """获取系统配置值"""
    return config_manager.get_config(key, default)


def get_model_config(model_id: int) -> Optional[Dict[str, Any]]:
    """获取模型配置"""
    return config_manager.get_model_config(model_id)


def get_model_by_config_key(config_key: str) -> Optional[Dict[str, Any]]:
    """通过配置键获取模型配置"""
    return config_manager.get_model_by_config_key(config_key)


def get_active_prompt(llm_type: int) -> Optional[str]:
    """获取指定 LLM 的最新 active prompt"""
    return config_manager.get_active_prompt(llm_type)


def clear_config_cache():
    """清空配置缓存"""
    config_manager.clear_cache()
