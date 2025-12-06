"""
Configuration management for the Royal Court.
Handles loading of jester.toml files for multi-realm setups.
"""
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

# Use tomllib for Python 3.11+, fallback to tomli if needed (though project requires 3.11+)
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore

@dataclass
class RealmConfig:
    name: str
    path: Path
    description: Optional[str] = None

@dataclass
class JesterConfig:
    model: str = "gemma3:4b"
    warrior_provider: str = "open-code"  # open-code or claude-code
    realms: List[RealmConfig] = field(default_factory=list)

    @classmethod
    def load(cls, path: Optional[Path] = None) -> 'JesterConfig':
        """Load configuration from a toml file"""
        # Search order: explicit path -> ./jester.toml -> ~/.jester.toml
        if path and path.exists():
            return cls._parse(path)
        
        local_config = Path("jester.toml")
        if local_config.exists():
            return cls._parse(local_config)
            
        home_config = Path.home() / ".jester.toml"
        if home_config.exists():
            return cls._parse(home_config)
            
        return cls()

    @classmethod
    def _parse(cls, path: Path) -> 'JesterConfig':
        try:
            with open(path, "rb") as f:
                data = tomllib.load(f)
            
            jester_data = data.get("jester", {})
            realms_data = data.get("realms", [])
            
            realms = []
            base_dir = path.parent
            
            for r in realms_data:
                # Resolve relative paths relative to config file
                realm_path = Path(r["path"])
                if not realm_path.is_absolute():
                    realm_path = (base_dir / realm_path).resolve()
                    
                realms.append(RealmConfig(
                    name=r["name"],
                    path=realm_path,
                    description=r.get("description")
                ))
                
            jester_data = data.get("jester", {})
            realms_data = data.get("realms", [])
            
            realms = []
            base_dir = path.parent
            
            for r in realms_data:
                # Resolve relative paths relative to config file
                realm_path = Path(r["path"])
                if not realm_path.is_absolute():
                    realm_path = (base_dir / realm_path).resolve()
                    
                realms.append(RealmConfig(
                    name=r["name"],
                    path=realm_path,
                    description=r.get("description")
                ))
                
            return cls(
                model=jester_data.get("model", "gemma3:4b"),
                warrior_provider=jester_data.get("warrior_provider", "open-code"),
                realms=realms
            )
        except Exception as e:
            print(f"Warning: Failed to load config from {path}: {e}")
            return cls()
