"""
Workflow Manager for Clara AI

This module coordinates the workflow and state transitions for email processing,
providing a structured approach to handle different email types.
"""

import logging
from typing import Dict, Any, List, Optional, Literal
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command
from langgraph.graph.message import add_messages
from agents.email_response import EmailResponse

class WorkflowState(TypedDict):
    """State maintained throughout the workflow."""
    email_input: dict
    messages: List[Dict[str, str]]  # Annotated[list, add_messages]  # Using regular list for clarity
    structured_response: Optional[EmailResponse]
    classification_result: Optional[str]

class WorkflowManager:
    """
    Manages the email processing workflow and state transitions.
    
    This class coordinates the different components involved in email processing,
    handling the flow between triage, response generation, and other stages.
    """
    
    def __init__(self, triage_system, response_generator, memory_manager):
        """
        Initialize the workflow manager.
        
        Args:
            triage_system: System for classifying emails
            response_generator: System for generating email responses
            memory_manager: System for managing workflow memory
        """
        self.logger = logging.getLogger("ClaraSecretary")
        self.triage_system = triage_system
        self.response_generator = response_generator
        self.memory_manager = memory_manager
        self.workflow = None
        self.user_profile = {}
        self.user_prompt_template = ""
        
    def configure(self, user_profile: Dict[str, str], user_prompt_template: str):
        """
        Configure the workflow manager.
        
        Args:
            user_profile: User profile information
            user_prompt_template: Template for user prompts
        """
        self.user_profile = user_profile
        self.user_prompt_template = user_prompt_template
        self._build_graph()
        
    def triage_router(self, state: WorkflowState) -> Command[Literal["response_agent", "__end__"]]:
        """
        Route emails based on triage classification.
        
        Args:
            state: Current workflow state
            
        Returns:
            Command: Direction for next workflow step
        """
        subject = state['email_input']['subject']
        email_thread = state['email_input']['email_thread']
        
        # Classify the email
        result = self.triage_system.classify_email(
            subject, 
            email_thread, 
            self.user_prompt_template
        )
        
        # Prepare update for state
        classification = result.classification
        update = {"classification_result": classification}
        
        # Route based on classification
        if result.classification == "respond":
            self.logger.info("📧 Classification: RESPOND - This email requires a response")
            goto = "response_agent"
            update.update({
                "messages": [
                    {
                        "role": "user",
                        "content": f"Draft a plain-text response to this email AS IF YOU ARE {self.user_profile['full_name']} (not as an assistant). Write in the first person from {self.user_profile['name']}'s perspective and sign with {self.user_profile['name']}'s name. NEVER respond as if you are anyone mentioned in the email other than {self.user_profile['full_name']}.\n\nSubject: {subject}\n\nThread: {email_thread}"
                    }
                ]
            })
        elif result.classification == "info_required":
            self.logger.info("🔔 Classification: INFO_REQUIRED - This email requires a response")
            goto = "response_agent" 
            update.update({
                "messages": [
                    {
                        "role": "user",
                        "content": f"Write a plain-text email response AS IF YOU ARE {self.user_profile['full_name']} (not as an assistant). Use [BRACKETS] to indicate any details that {self.user_profile['name']} needs to provide. Write in the first person from {self.user_profile['name']}'s perspective and sign with {self.user_profile['name']}'s name. NEVER respond as if you are anyone mentioned in the email other than {self.user_profile['full_name']}.\n\nSubject: {subject}\n\nEmail Thread:\n{email_thread}"
                    }
                ]
            })
        elif result.classification == "ignore":
            self.logger.info("🚫 Classification: IGNORE - This email can be safely ignored")
            goto = END
        elif result.classification == "notify":
            self.logger.info("🔔 Classification: NOTIFY - This email contains important information")
            goto = END
        else:
            raise ValueError(f"Invalid classification: {result.classification}")
        
        return Command(goto=goto, update=update)
    
    def _build_graph(self):
        """Build the workflow graph with nodes and transitions."""
        # Create a new workflow
        workflow = StateGraph(WorkflowState)
        
        # Add nodes
        workflow.add_node("triage_router", self.triage_router)
        workflow.add_node("response_agent", self.response_generator.get_agent())
        
        # Configure edges
        workflow = workflow.add_edge(START, "triage_router")
        
        # Compile the workflow with the memory store
        self.workflow = workflow.compile(store=self.memory_manager.get_store())
        self.logger.debug("Workflow graph built and compiled")
        
    def process_email(self, email_input: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> Any:
        """
        Process an email through the workflow.
        
        Args:
            email_input: Email data to process
            config: Optional configuration parameters
            
        Returns:
            The result of the workflow execution
        """
        if not self.workflow:
            raise ValueError("Workflow not configured. Call configure() first.")
            
        response = self.workflow.invoke(
            email_input,
            config=config
        )
        return response