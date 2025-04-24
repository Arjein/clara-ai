"""
Email Triage System for Clara AI

This module provides email classification and routing functionality for Clara AI.
It uses LLM models to analyze emails and determine appropriate handling.
"""

import logging
from typing import Dict, Any, Optional
from langchain_core.language_models import BaseChatModel
from agents.email_response import Router
from objects.mail_thread import MailThread

class EmailTriageSystem:
    """
    Handles email classification and routing decisions.
    
    This class uses LLM models to analyze incoming emails and classify them
    according to predefined categories, determining how they should be processed.
    """
    
    def __init__(self, llm: BaseChatModel, system_prompt_template: str):
        """
        Initialize the email triage system.
        
        Args:
            llm: Language model for classification
            system_prompt_template: Template for the system prompt with placeholders
        """
        self.logger = logging.getLogger("ClaraSecretary")
        self.llm = llm.with_structured_output(Router)
        self.system_prompt_template = system_prompt_template
        self.system_prompt = ""
        
    def configure(self, triage_rules: Dict[str, str], user_profile: Dict[str, str]) -> None:
        """
        Configure the triage system with rules and user profile.
        
        Args:
            triage_rules: Dictionary of triage rules for each category
            user_profile: User profile information
        """
        self.system_prompt = self.system_prompt_template.format(
            full_name=user_profile["full_name"],
            name=user_profile["name"],
            examples=None,
            user_profile_background=user_profile["user_profile_background"],
            triage_no=triage_rules["ignore"],
            triage_notify=triage_rules["notify"],
            triage_info_required=triage_rules["info_required"],
            triage_email=triage_rules["respond"],
        )
        self.logger.debug("Triage system configured with rules and user profile")
    
    def classify_email(self, subject: str, email_thread: str, user_prompt_template: str) -> Router:
        """
        Classify an email using the configured LLM.
        
        Args:
            subject: Email subject
            email_thread: Full email thread content
            user_prompt_template: Template for user prompt
            
        Returns:
            Router: Classification result with reasoning
        """
        if not self.system_prompt:
            raise ValueError("Triage system not configured. Call configure() first.")
            
        user_prompt = user_prompt_template.format(
            subject=subject, 
            email_thread=email_thread
        )
        
        result = self.llm.invoke(
            [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_prompt},
            ]
        )
        
        self.logger.info(f"Email classified as: {result.classification}")
        self.logger.debug(f"Classification reasoning: {result.reasoning}")
        
        return result