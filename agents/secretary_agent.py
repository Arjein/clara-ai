"""
Secretary Agent for Clara AI

This module provides the main Secretary Agent that coordinates the email processing system.
It acts as a facade that integrates all the specialized components into a cohesive system.
"""

import os
import logging
import dotenv
from typing import Dict, Any, List, Optional
from langchain.chat_models import init_chat_model
from user import AppUser
from agents.email_response import Router, EmailResponse
from agents.agent_tools import get_current_date, manage_memory_tool, search_memory_tool
from agents.prompts import agent_system_prompt_memory, triage_system_prompt, triage_user_prompt
from agents.memory_manager import MemoryManager
from agents.email_triage import EmailTriageSystem
from agents.response_generator import ResponseGenerator
from agents.workflow_manager import WorkflowManager

_ = dotenv.load_dotenv()

class SecretaryAgent:
    """
    Main agent class that coordinates email processing components.
    
    This class acts as a facade, integrating the specialized components:
    - Memory management
    - Email triage/classification
    - Response generation
    - Workflow coordination
    
    It maintains the same functionality as before but with improved modularity.
    """
    
    def __init__(self, user_profile = None, model_name='mixtral:8x7b-instruct'):
        """
        Initialize the secretary agent with its component systems.
        
        Args:
            user_profile: Optional user profile to override defaults
            model_name: Name of the Ollama model to use (default: mixtral:8x7b-instruct)
                        Other good options: llama3:70b, claude-3-haiku, mistral:7b-instruct
        """
        self.logger = logging.getLogger("ClaraSecretary")
        
        # Initialize the language model with the specified model
        self.logger.info(f"Initializing language model with: {model_name}")
        self.llm = init_chat_model(model=model_name, model_provider='ollama')
        
        # Configure user profile
        self.profile = self._init_user_profile(user_profile)
        self.logger.info(f"User Profile: {self.profile}")
        
        # Configuration for langgraph
        self.config = {"configurable": {'langgraph_user_id': AppUser.email}}
        
        # Define triage rules and agent instructions
        self.prompt_instructions = self._init_prompt_instructions()
        
        # Initialize component systems
        self.memory_manager = MemoryManager()
        self.tools = self._init_tools()
        self.triage_system = EmailTriageSystem(self.llm, triage_system_prompt)
        self.response_generator = ResponseGenerator(self.llm, agent_system_prompt_memory, self.tools)
        self.workflow_manager = WorkflowManager(
            self.triage_system, 
            self.response_generator,
            self.memory_manager
        )
        
        # Configure all components
        self._configure_components()
        
    def _init_user_profile(self, user_profile) -> Dict[str, str]:
        """Initialize the user profile with defaults or overrides."""
        if user_profile:
            return user_profile
            
        return {
            "name": AppUser.name,
            "full_name": AppUser.get_full_name(),
            "user_profile_background": "Recent Graduate with BSc in Computer Engineering and MSc in Engineering with Management. Who have a passion for AI/ML Engineering",
        }
        
    def _init_prompt_instructions(self) -> Dict[str, Any]:
        """Initialize the triage rules and agent instructions."""
        return {
            "triage_rules": {
                "ignore": "Marketing newsletters, spam emails, mass company announcements",
                "notify": "Team member out sick, build system notifications, project status updates",
                "info_required": f"Questions that need additional information from {self.profile['name']}, meeting requests, critical bug reports",
                "respond": "Direct questions that requires no additional information, such as celebration, gratitude, and appreciation",
            },
            "agent_instructions": f"Use these tools when appropriate to help manage {self.profile['name']}'s tasks efficiently."
        }
        
    def _init_tools(self) -> List[Any]:
        """Initialize the tools for the response agent."""
        return [
            get_current_date, 
            manage_memory_tool,
            search_memory_tool,
        ]
        
    def _configure_components(self) -> None:
        """Configure all component systems with the necessary settings."""
        # Configure triage system
        self.triage_system.configure(
            self.prompt_instructions["triage_rules"],
            self.profile
        )
        
        # Configure response generator
        self.response_generator.configure(
            self.profile,
            self.prompt_instructions["agent_instructions"],
            self.memory_manager.get_store()
        )
        
        # Configure workflow manager
        self.workflow_manager.configure(
            self.profile,
            triage_user_prompt
        )
        
    def generate_response(self, email_input: Dict[str, Any]) -> Any:
        """
        Generate a response for the given email.
        
        This method routes the email through the workflow system and returns the result.
        
        Args:
            email_input: Dictionary containing email subject and thread content
            
        Returns:
            The processed response from the workflow
        """
        return self.workflow_manager.process_email(
            email_input,
            config=self.config
        )