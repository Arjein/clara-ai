from pydantic import BaseModel, Field
from typing_extensions import TypedDict, Literal, Annotated

# Define the structured email output model

class Router(BaseModel):
    """Analyze the unread email and route it according to its content."""

    reasoning: str = Field(
        description="Step-by-step reasoning behind the classification."
    )
    classification: Literal["ignore", "respond", "notify", 'info_required'] = Field(
        description="The classification of an email: 'ignore' for irrelevant emails, "
        "'notify' for important information that doesn't need a response, "
        "'respond' for emails that need a reply and do not require more information from user, "
        "'info_required' for emails that needs more information before responding",
    )


class EmailResponse(BaseModel):
    """Structured email response format for responses written AS the user (not on behalf of anyone else)."""
    greeting: str = Field(description="The salutation/greeting at the beginning of the email. Remember you are writing AS the user.")
    content: str = Field(description="The main body text of the email (without greetings and signature). The content must be written from the user's perspective, never as someone else.")
    signature: str = Field(description="The closing signature of the email, which should include the user's name")
    
    @classmethod
    def format_email(cls, response) -> str:
        """Format the email components into a complete email"""
        if isinstance(response, dict):
            formatted_email = f"{response['greeting']}\n\n"
            formatted_email += f"{response['content']}\n\n"
            formatted_email += f"{response['signature']}\n"
        elif isinstance(response, cls):
            formatted_email = f"{response.greeting}\n\n"
            formatted_email += f"{response.content}\n\n"
            formatted_email += f"{response.signature}\n"
        else:
            # Fallback if response is just text
            return str(response)
        
        return formatted_email
