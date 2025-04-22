from langgraph.prebuilt import create_react_agent, ToolNode
import os
import dotenv
from typing import Annotated, Any, Dict, Optional, List, Union, Literal
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.types import Command
from langchain_openai import AzureChatOpenAI
from langchain.tools import tool
from pydantic import BaseModel, Field
from datetime import datetime
from user import AppUser
from objects.mail_thread import MailThread
from agents.email_response import Router, EmailResponse
from agents.agent_tools import get_current_date, write_email, schedule_meeting, check_calendar_availability
from agents.prompts import agent_system_prompt, triage_system_prompt, triage_user_prompt

_ = dotenv.load_dotenv()

class State(TypedDict):
    email_input: dict
    messages: Annotated[list, add_messages]
    final_response: Optional[EmailResponse]
    classification_result: Optional[str]  # Add this field

class SecretaryAgent:
    def __init__(self, user_profile = None):
        self.llm = AzureChatOpenAI(
            model='o3-mini',
            azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            api_key=os.environ["AZURE_OPENAI_API_KEY"],
            openai_api_version=os.environ["AZURE_OPENAI_API_VERSION"],
        )
        self.profile = {
            "name": AppUser.name,
            "full_name": AppUser.get_full_name(),
            "user_profile_background": "Recent Graduate with BSc in Computer Engineering and MSc in Engineering with Management. Who have a passion for AI/ML Engineering",
        }
        print('User Profile:', self.profile)
        
        self.prompt_instructions = {
            "triage_rules": {
                "ignore": "Marketing newsletters, spam emails, mass company announcements",
                "notify": "Team member out sick, build system notifications, project status updates",
                "info_required": f"Questions that need additional information from {self.profile['name']}, meeting requests, critical bug reports",
                "respond": "Direct questions that requires no additional information, such as celebration, gratitude, and appreciation",
            },
            "agent_instructions": f"Use these tools when appropriate to help manage {self.profile['name']}'s tasks efficiently."
        }
        self.llm_router = self.llm.with_structured_output(Router)

        self.system_prompt = triage_system_prompt.format(
            full_name=self.profile["full_name"],
            name=self.profile["name"],
            examples=None,
            user_profile_background=self.profile["user_profile_background"],
            triage_no=self.prompt_instructions["triage_rules"]["ignore"],
            triage_notify=self.prompt_instructions["triage_rules"]["notify"],
            triage_info_required=self.prompt_instructions["triage_rules"]["info_required"],
            triage_email=self.prompt_instructions["triage_rules"]["respond"],
        )
        
        self.tools = [write_email, get_current_date, EmailResponse]
        self.secretary_agent = self._build_graph()
    
    def create_prompt(self, state):
        system_content = agent_system_prompt.format(
            instructions=self.prompt_instructions["agent_instructions"],
            **self.profile
        )
        
        # Add instructions to use EmailResponse tool for the final answer
        system_content += "\n\nFor your final response, use the EmailResponse tool with these fields: reasoning, subject, greeting, content, signature, recipient_name, and sender_name."
        
        return [
            {"role": "system", "content": system_content}
        ] + state['messages']
    
    def triage_router(self, state: State) -> Command[Literal["agent", "__end__"]]:
        subject = state['email_input']['subject']
        email_thread = state['email_input']['email_thread']

        user_prompt = triage_user_prompt.format(
            subject=subject, 
            email_thread=email_thread
        )
        
        result = self.llm_router.invoke(
            [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_prompt},
            ]
        )
        
        print('Classification Result:', result)
        classification = result.classification
        update = {"classification_result": classification}
    
        if result.classification == "respond":
            print("📧 Classification: RESPOND - This email requires a response")
            goto = "agent"
            update.update({
                "messages": [
                    {
                        "role": "user",
                        "content": f"Draft a response to this email on behalf of {self.profile['full_name']}:\n\nSubject: {subject}\n\nThread: {email_thread}"
                    }
                ]
            })

        elif result.classification == "info_required":
            print("🔔 Classification: INFO_REQUIRED - This email requires a response")
            goto = "agent" 
            # TODO: Burayi daha saglam yapman lazim!
            update.update({
                "messages": [
                    {
                        "role": "user",
                        "content": f"Write an email response as if you are {self.profile['full_name']}. Use [BRACKETS] to indicate any details that {self.profile['name']} needs to provide, such as confirming a time, granting permission, or adding missing information.\n\nSubject: {subject}\n\nEmail Thread:\n{email_thread}"
                    }
                ]
            })

        elif result.classification == "ignore":
            print("🚫 Classification: IGNORE - This email can be safely ignored")
            update = update
            goto = END
        elif result.classification == "notify":
            print("🔔 Classification: NOTIFY - This email contains important information")
            update = update
            goto = END
        else:
            raise ValueError(f"Invalid classification: {result.classification}")
        
        return Command(goto=goto, update=update)
    
    def call_model(self, state: State):
        # Bind the tools to the model with tool_choice="any" to force tool usage
        model_with_tools = self.llm.bind_tools(self.tools, tool_choice="any")
        
        # Call the model with the current messages
        response = model_with_tools.invoke(self.create_prompt(state))
        
        # Return the model's response to be added to messages
        return {"messages": [response]}
    
    def should_continue(self, state: State):
        messages = state["messages"]
        last_message = messages[-1]
        
        # Check if the last message has tool calls
        if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
            return "continue"
        
        # If there is an EmailResponse tool call, process it
        for tool_call in last_message.tool_calls:
            if tool_call["name"] == "EmailResponse":
                return "respond"
        
        # Otherwise continue with tools
        return "continue"
    
    def respond(self, state: State):
        messages = state["messages"]
        last_message = messages[-1]
        
        # Find the EmailResponse tool call
        email_response_call = None
        for tool_call in last_message.tool_calls:
            if tool_call["name"] == "EmailResponse":
                email_response_call = tool_call
                break
        
        if not email_response_call:
            raise ValueError("No EmailResponse tool call found")
        
        # Create an EmailResponse from the tool call arguments
        email_response = EmailResponse(**email_response_call["args"])
        
        # Create a tool message
        tool_message = {
            "type": "tool",
            "content": "Email response created successfully",
            "tool_call_id": email_response_call["id"]
        }
        
        # Return the final response and add the tool message
        return {"final_response": email_response, "messages": [tool_message]}
    
    def _build_graph(self):
        # Create a new workflow
        workflow = StateGraph(State)
        
        # Add nodes
        workflow.add_node("triage_router", self.triage_router)
        workflow.add_node("agent", self.call_model)
        workflow.add_node("tools", ToolNode(self.tools))
        workflow.add_node("respond", self.respond)
        
        # Set entry point - use "triage_router" as the entry point
        workflow.set_entry_point("triage_router")
        
        # Add edges (don't connect START explicitly)
        workflow.add_edge("triage_router", "agent")
        
        # Add conditional edges from agent
        workflow.add_conditional_edges(
            "agent",
            self.should_continue,
            {
                "continue": "tools",
                "respond": "respond"
            }
        )
        
        # Complete the cycle
        workflow.add_edge("tools", "agent")
        workflow.add_edge("respond", END)
        
        return workflow.compile()
    


