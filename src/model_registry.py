"""Model registry: loads model metadata, pricing, and defaults from YAML."""

from typing import Any, Dict, List, Optional, Union
from pathlib import Path
import yaml
import os


class ModelRegistry:
    """Manages model configurations and provides access to model metadata."""
    
    def __init__(self, config_path: Union[str, Path]):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.region_name = self.config.get("region_name", os.getenv("AWS_REGION", "us-east-1"))
    
    def _load_config(self) -> Dict[str, Any]:
        """Load YAML configuration file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Model config not found: {self.config_path}")
        
        with open(self.config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    
    def list_models(self) -> List[Dict[str, Any]]:
        """Return list of all configured models."""
        return list(self.config.get("models", []))
    
    def get_model_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get model configuration by name."""
        for model in self.list_models():
            if model.get("name") == name:
                return model
        return None
    
    def get_models_by_names(self, names: List[str]) -> List[Dict[str, Any]]:
        """Get multiple model configurations by names."""
        if "all" in names:
            return self.list_models()
        
        models = []
        for name in names:
            model = self.get_model_by_name(name)
            if model:
                models.append(model)
        return models
    
    def get_model_pricing(self, model: Dict[str, Any]) -> Dict[str, float]:
        """Extract pricing information from model config."""
        pricing = model.get("pricing", {})
        return {
            "input_per_1k_tokens_usd": float(pricing.get("input_per_1k_tokens_usd", 0.0)),
            "output_per_1k_tokens_usd": float(pricing.get("output_per_1k_tokens_usd", 0.0))
        }
    
    def get_generation_params(self, model: Dict[str, Any]) -> Dict[str, Any]:
        """Extract generation parameters from model config."""
        return model.get("generation_params", {})


# Convenience functions for backward compatibility
def load_models_config(config_path: Union[str, Path]) -> Dict[str, Any]:
    """Load models configuration from YAML file."""
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def list_models(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """List all models from config."""
    return list(config.get("models", []))


def get_model_by_name(config: Dict[str, Any], name: str) -> Optional[Dict[str, Any]]:
    """Get model by name from config."""
    for m in config.get("models", []):
        if m.get("name") == name:
            return m
    return None


