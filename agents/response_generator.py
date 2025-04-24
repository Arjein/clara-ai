"""
Response Generator for Clara AI

This module handles the generation of email responses based on classified emails.
It creates properly formatted replies using the appropriate tone and context.
"""

import logging
from typing import Dict, Any, List, Optional
from langchain_core.language_models import BaseChatModel
from langgraph.prebuilt import create_react_agent
from agents.email_response import EmailResponse

class ResponseGenerator:
    """
    Generates appropriate email responses based on email classification.
    
    This class manages the LLM-based agent that generates email responses
    with the right format, tone, and content based on the email context.
    """
    
    def __init__(self, llm: BaseChatModel, agent_system_prompt_template: str, tools: List[Any]):
        """
        Initialize the response generator.
        
        Args:
            llm: Language model for response generation
            agent_system_prompt_template: Template for the agent's system prompt
            tools: List of tools available to the agent
        """
        self.logger = logging.getLogger("ClaraSecretary")
        self.llm = llm
        self.agent_system_prompt_template = agent_system_prompt_template
        self.tools = tools
        self.response_agent = None
        self.user_profile = {}
        
    def configure(self, user_profile: Dict[str, str], agent_instructions: str, store: Any) -> None:
        """
        Configure the response generator with user profile and instructions.
        
        Args:
            user_profile: User profile information
            agent_instructions: Instructions for the agent
            store: Memory store for the agent
        """
        self.user_profile = user_profile
        self.agent_instructions = agent_instructions
        
        # Create the response agent
        self.response_agent = create_react_agent(
            self.llm,
            tools=self.tools,
            prompt=self.create_prompt,
            store=store,
            response_format=EmailResponse
        )
        
        self.logger.debug("Response generator configured with user profile and memory store")
        
    def create_prompt(self, state: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Create the prompt for the response agent.
        
        Args:
            state: Current state of the conversation
            
        Returns:
            List of messages for the agent prompt
        """
        system_content = self.agent_system_prompt_template.format(
            instructions=self.agent_instructions,
            **self.user_profile
        )
        
        return [
            {
                "role": "system", 
                "content": system_content
            },
        ] + state.get('messages', [])
    
    def get_agent(self) -> Any:
        """
        Get the configured response agent.
        
        Returns:
            The configured response agent
        """
        if not self.response_agent:
            raise ValueError("Response generator not configured. Call configure() first.")
            
        return self.response_agent