"""
Agent Manager for VoltaireAI

Loads and manages AI agents based on configuration.
"""

import json
import os
from typing import Dict, Any, Optional, List
from api.models import IntentType
import logging

logger = logging.getLogger(__name__)

class AgentManager:
    """
    Manages AI agents for different tasks.

    Loads agents from config/agents.json and provides
    agent selection, CRUD, and execution functionality.
    """

    def __init__(self, config_path: str = None):
        """
        Initialize AgentManager.

        Args:
            config_path: Path to agents configuration file
        """
        self.agents = {}
        self.config_path = None
        self._loaded_mtime = 0.0

        if config_path is None:
            possible_paths = [
                "config/agents.json",
                "backend/config/agents.json",
                os.path.join(os.path.dirname(__file__), "../config/agents.json")
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    config_path = path
                    break

        if config_path:
            self.config_path = config_path
            self.load_agents(config_path)
        else:
            logger.warning("Agents config not found in any location")

    def load_agents(self, config_path: str) -> None:
        """Load agents from JSON configuration."""
        if not os.path.exists(config_path):
            logger.warning(f"Agents config not found: {config_path}")
            return

        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        self.agents = {}
        for agent_config in config.get('agents', []):
            agent_id = agent_config['id']
            self.agents[agent_id] = agent_config

        self._loaded_mtime = os.path.getmtime(config_path)
        logger.info(f"Loaded {len(self.agents)} agents")

    def _check_reload(self) -> None:
        """Reload agents from file if modified since last load."""
        if not self.config_path or not os.path.exists(self.config_path):
            return
        current_mtime = os.path.getmtime(self.config_path)
        if current_mtime > self._loaded_mtime:
            logger.info("Agents config changed, reloading...")
            self.load_agents(self.config_path)

    def save_agents(self) -> None:
        """Save current agents to config file."""
        if not self.config_path:
            logger.error("No config path set, cannot save agents")
            return

        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump({"agents": list(self.agents.values())}, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved {len(self.agents)} agents to {self.config_path}")

    def get_agent_by_intent(self, intent: IntentType) -> Optional[Dict[str, Any]]:
        """Select agent based on user intent."""
        self._check_reload()
        agent_type = "operation" if intent == IntentType.OPERATION else "question"

        for agent_id, agent_config in self.agents.items():
            if agent_config.get('type') == agent_type:
                logger.info(f"Selected agent: {agent_id} for intent: {intent}")
                return agent_config

        logger.warning(f"No agent found for intent: {intent}")
        return None

    def get_agent_by_id(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get agent by ID."""
        self._check_reload()
        return self.agents.get(agent_id)

    def list_agents(self) -> List[Dict[str, Any]]:
        """List all available agents with full config."""
        self._check_reload()
        return list(self.agents.values())

    def update_agent(self, agent_id: str, config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Update or create an agent.

        Args:
            agent_id: Agent identifier
            config: New agent configuration

        Returns:
            Updated agent config or None
        """
        self._check_reload()
        config['id'] = agent_id
        self.agents[agent_id] = config
        self.save_agents()
        logger.info(f"Updated agent: {agent_id}")
        return config

    def delete_agent(self, agent_id: str) -> bool:
        """
        Delete an agent by ID.

        Args:
            agent_id: Agent identifier

        Returns:
            True if deleted, False if not found
        """
        self._check_reload()
        if agent_id in self.agents:
            del self.agents[agent_id]
            self.save_agents()
            logger.info(f"Deleted agent: {agent_id}")
            return True
        logger.warning(f"Agent not found for deletion: {agent_id}")
        return False

    def list_agent_ids(self) -> List[str]:
        """List all available agent IDs."""
        return list(self.agents.keys())


# Singleton instance
_agent_manager: Optional[AgentManager] = None


def get_agent_manager() -> AgentManager:
    global _agent_manager
    if _agent_manager is None:
        _agent_manager = AgentManager()
    return _agent_manager