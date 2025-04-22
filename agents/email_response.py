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
    """Structured email response format."""
    greeting: str = Field(description="The salutation/greeting at the beginning of the email")
    content: str = Field(description="The main body text of the email (without greetings and signature)")
    signature: str = Field(description="The closing signature of the email")
    
    def format_email(self) -> str:
        """Format the email components into a complete email"""
        formatted_email = f"{self.greeting}\n\n"
        formatted_email += f"{self.content}\n\n"
        formatted_email += f"{self.signature}\n"
        
        return formatted_email
    
#     def complete_email(self) -> str:
#         """Return a complete email with subject and formatted body"""
#         #return f"Subject: {self.subject}\n\nTo: {self.recipient_name}\n\n{self.format_email()}\n\nFrom: {self.sender_name}"
#         return f"{self.format_email()}"