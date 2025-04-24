from langchain.tools import tool
import datetime
from datetime import datetime
from langmem import create_manage_memory_tool, create_search_memory_tool



manage_memory_tool = create_manage_memory_tool(
    namespace=(
        "email_assistant", 
        "{langgraph_user_id}",
        "collection"
    )
)
search_memory_tool = create_search_memory_tool(
    namespace=(
        "email_assistant",
        "{langgraph_user_id}",
        "collection"
    )
)

@tool
def get_current_date() -> str:
    """Get the current date and time with day name."""
    return datetime.now().strftime("%Y-%m-%d, %A, %H:%M")

# @tool
# def write_email(to: str, subject: str, content: str) -> str:
#     """Write and send an email."""
#     # Placeholder response - in real app would send email
#     return f"Email sent to {to} with subject '{subject}'"
