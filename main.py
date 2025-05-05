"""
Clara AI - Gmail Assistant

This application serves as an AI-powered email assistant that works with Gmail to help
manage and respond to your inbox. It provides the following key features:

- Automatically monitoring Gmail inbox for new messages
- Classifying and organizing emails with Gmail labels
- Generating intelligent draft responses
- Maintaining thread state through Gmail labels
- Operating on a configurable polling interval

The application uses OAuth2 for Gmail authentication and leverages Gmail's API
for all email operations while storing user details and last email update times in a JSON file.
"""
import json
import logging
import argparse
import signal
import sys
import time
import traceback
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn, TimeRemainingColumn
from rich.table import Table
from rich import print as rprint
from agents.secretary_agent import SecretaryAgent
from objects.gmail_handler import GmailHandler
from user import AppUser
from datetime import datetime, timedelta, timezone
from helpers import get_threads_require_process, process_thread


# Create console instance for rich output
console = Console()

# Create module-level logger
logger = None

def setup_logging(debug=False, log_file="clara_secretary.log", quiet=False):
    """
    Set up logging configuration
    
    Args:
        debug: Whether to enable debug logging
        log_file: Path to the log file
        quiet: If True, suppress console logging and only log to file
    """
    level = logging.DEBUG if debug else logging.INFO
    
    # Configure basic file logging
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    
    # Set up the logger
    logger = logging.getLogger("ClaraSecretary")
    logger.setLevel(level)
    logger.handlers = []  # Clear any existing handlers
    logger.addHandler(file_handler)
    
    # Add console handler only if quiet mode is not enabled
    if not quiet:
        # Configure rich console logging
        rich_handler = RichHandler(rich_tracebacks=True, console=console)
        logger.addHandler(rich_handler)
    
    return logger

def parse_arguments():
    """Parse command line arguments with enhanced options"""
    parser = argparse.ArgumentParser(
        description='Clara AI - Your E-mail Assistant',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Core settings
    parser.add_argument('--interval', type=int, default=20,
                        help='Check interval in seconds')
    parser.add_argument('--limit', type=int, default=50,
                        help='Maximum number of emails to fetch')
    
    # AI model settings
    parser.add_argument('--model', type=str, 
                        help='Ollama model to use (e.g., mistral:7b-instruct-q4_0, llama3:70b)')
    
    # Logging and display options
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug logging')
    parser.add_argument('--log-file', type=str, default="clara_secretary.log",
                        help='Path to log file')
    parser.add_argument('--quiet', action='store_true',
                        help='Minimal console output')
    
    return parser.parse_args()

def display_banner():
    """Display a welcome banner with app information"""
    banner_text = """
    [bold blue]Clara AI[/bold blue] - [italic]Your Email Assistant[/italic]
    
    Helping you manage your inbox smartly and efficiently
    """
    console.print(Panel(banner_text, expand=False, border_style="blue"))

def display_status(last_update, user_email):
    """Display the current status of the application"""
    table = Table(title="Clara AI Status")
    
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("User Email", user_email)
    table.add_row("Last Update", str(last_update) if last_update else "Not Initialized")
    
    console.print(table)

def handle_exit(signum, frame):
    """Handle exit signals gracefully"""
    global logger
    logger.warning("Received exit signal. Shutting down Clara Secretary...")
    sys.exit(0)

def ensure_timezone_aware(dt_obj, default_tz=None):
    """Ensure a datetime object has timezone information, handling various formats
    
    This function handles datetime objects from different sources (Gmail API, local system)
    with potentially different timezone information or no timezone information at all.
    
    Args:
        dt_obj: A datetime object or string to ensure has timezone info
        default_tz: The timezone to use if none is present (defaults to system local timezone)
        
    Returns:
        A timezone-aware datetime object, or None if conversion failed
    """
    if not dt_obj:
        return None
    
    # Get system's local timezone if not specified
    if default_tz is None:
        import datetime as dt
        default_tz = dt.datetime.now().astimezone().tzinfo
    
    # Handle string datetime objects with multiple possible formats
    if isinstance(dt_obj, str):
        # Try various formats, starting with the most precise
        formats_to_try = [
            None,  # First try fromisoformat which handles ISO 8601 formats
            "%Y-%m-%d %H:%M:%S.%f%z",
            "%Y-%m-%dT%H:%M:%S.%f%z",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%d %H:%M:%S",
            "%a, %d %b %Y %H:%M:%S %z",  # RFC 2822 format (email headers)
            "%a, %d %b %Y %H:%M:%S",
        ]
        
        dt_parsed = None
        for fmt in formats_to_try:
            try:
                if fmt is None:
                    # Use fromisoformat which preserves timezone info
                    dt_parsed = datetime.fromisoformat(dt_obj)
                else:
                    dt_parsed = datetime.strptime(dt_obj, fmt)
                break
            except (ValueError, TypeError):
                continue
        
        if dt_parsed is None:
            logger.warning(f"Could not parse datetime string: {dt_obj}")
            return None
        
        dt_obj = dt_parsed
    
    # Add timezone if it's naive
    if dt_obj.tzinfo is None:
        dt_obj = dt_obj.replace(tzinfo=default_tz)
    
    return dt_obj

def get_safe_datetime(thread, min_datetime=datetime.min.replace(tzinfo=timezone.utc)):
    """Function to safely get last_updated with consistent timezone"""
    if not thread.last_updated:
        return min_datetime
    else:
        # If it already has timezone info, convert to UTC
        return thread.last_updated.astimezone(timezone.utc)

def authenticate_gmail():
    """Authenticate with Gmail and return handler"""
    with console.status("[bold green]Authenticating with Gmail...", spinner="dots"):
        gmail_handler = GmailHandler()
    
    # Make sure we have a valid user email
    if not AppUser.email:
        logger.error("Error: Could not determine user email from Gmail authentication")
        console.print("[bold red]Error: Could not determine user email from Gmail authentication[/bold red]")
        exit(1)
    
    logger.info(f"Using authenticated user: {AppUser.email}")
    return gmail_handler

def initialize_user_profile():
    """Initialize or load user profile"""
    with console.status("[bold green]Loading user profile from JSON file...", spinner="dots"):
        user_exists = AppUser.load_from_json(AppUser.email)
        if not user_exists:
            logger.info(f"Creating new user profile for {AppUser.email}")
            AppUser.save_as_json()
        else:
            logger.info(f"Loaded existing user profile for {AppUser.email}")

def get_initial_update_time():
    """Get the last email update time from user data"""
    with console.status("[bold green]Getting last email update time from user data...", spinner="dots"):
        last_update = AppUser.get_last_email_update_time()
        if last_update:
            try:
                last_update = datetime.fromisoformat(last_update)
            except ValueError:
                logger.warning(f"Invalid last update time format in user data: {last_update}")
                last_update = None
        else:
            logger.info("Last Email Update: Not Initialized")
    
    return last_update

def build_gmail_query(last_update):
    """Build Gmail API query based on last update time"""
    query = 'category:primary'
    if last_update:
        # Get the timestamp directly from last_update
        timestamp_seconds = int(last_update.timestamp()) + 15
        
        # Use the timestamp directly in the query
        query += f" after:{timestamp_seconds}"
    
    return query

def fetch_gmail_threads(gmail_handler, query, limit):
    """Fetch threads from Gmail using the provided query"""
    with console.status(f"[bold green]Fetching emails with query: {query}...", spinner="dots"):
        all_threads = gmail_handler.fetch_threads( 
            user_id='me', 
            query=query, 
            limit=limit,
        )
    
    # Display fetched threads
    if all_threads:
        logger.info(f"Found {len(all_threads)} emails to process")
        console.print(f"\n[bold green]Found {len(all_threads)} emails to process:[/bold green]")
        for t in all_threads:
            logger.debug(f"Thread: {t.subject}")
            console.print(f"  • [cyan]{t.subject}[/cyan]")
    else:
        logger.info("No new emails found")
        console.print("[yellow]No new emails found[/yellow]")
    
    return all_threads

def process_email_threads(threads, gmail_handler, secretary_agent):
    """Process email threads that need attention"""
    threads_require_process = get_threads_require_process(threads)
    if not threads_require_process:
        return
    
    logger.info(f"Processing {len(threads_require_process)} emails that require attention")
    console.print(f"\n[bold green]Processing {len(threads_require_process)} emails that require attention...[/bold green]")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        process_task = progress.add_task("Processing emails", total=len(threads_require_process))
        
        for thread in threads_require_process:
            progress.update(process_task, advance=1, description=f"Processing: {thread.subject[:40]}...")
            process_thread(thread, gmail_handler, secretary_agent, logger)

def update_last_email_timestamp(all_threads):
    """Update the last email timestamp from threads if needed"""
    if not all_threads:
        return None
    
    min_datetime = datetime.min.replace(tzinfo=timezone.utc)
    newest_thread = max(all_threads, key=lambda t: get_safe_datetime(t, min_datetime))
    last_update = newest_thread.last_updated
    
    # Ensure last_update has timezone information
    last_update = ensure_timezone_aware(last_update)
    if not last_update:
        return None
    
    # Get the current last update time from JSON file
    current_db_time = AppUser.get_last_email_update_time()
    if current_db_time:
        current_datetime = ensure_timezone_aware(current_db_time)
        if current_datetime and last_update > current_datetime:
            AppUser.update_last_email_time(last_update)
    else:
        # If no current time stored, update
        AppUser.update_last_email_time(last_update)
    
    return last_update

def wait_for_next_check(interval):
    """Wait for the next check with a progress bar"""
    next_check_time = datetime.now() + timedelta(seconds=interval)
    logger.info(f"Waiting until next check ({next_check_time.strftime('%H:%M:%S')})")
    
    # Countdown timer for next check
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold green]Next check in:[/bold green]"),
        BarColumn(),
        TimeRemainingColumn(),
        console=console
    ) as progress:
        wait_task = progress.add_task("Waiting", total=interval)
        remaining_time = interval
        
        while remaining_time > 0:
            time.sleep(1)
            remaining_time -= 1
            progress.update(wait_task, completed=interval - remaining_time)

def process_emails(gmail_handler, secretary_agent, last_update, args):
    """Main email processing function"""
    try:
        # Build Gmail query based on last update time
        query = build_gmail_query(last_update)
        
        # Fetch threads with the query
        all_threads = fetch_gmail_threads(gmail_handler, query, args.limit)
        
        # Process threads that need attention
        process_email_threads(all_threads, gmail_handler, secretary_agent)
        
        # Update timestamp from the latest thread if available
        updated_timestamp = update_last_email_timestamp(all_threads)
        if updated_timestamp:
            last_update = updated_timestamp
        
        # Wait for next check
        wait_for_next_check(args.interval)
        
        return last_update
        
    except Exception as e:
        logger.error(f"Error in main processing loop: {e}")
        logger.debug(traceback.format_exc())
        console.print(f"[bold red]Error encountered: {e}[/bold red]")
        logger.warning(f"Retrying in 60 seconds...")
        console.print("[yellow]Retrying in 60 seconds...[/yellow]")
        time.sleep(60)
        return last_update

def main():
    global logger
    
    # Set up signal handlers for graceful exit
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)
    
    # Parse arguments
    args = parse_arguments()
    
    # Display welcome banner
    display_banner()
    
    # Set up logging - pass the quiet flag from command line arguments
    logger = setup_logging(args.debug, args.log_file, args.quiet)
    
    # Authenticate with Gmail
    gmail_handler = authenticate_gmail()
    
    # Load or create user profile
    initialize_user_profile()
    
    # Initialize the SecretaryAgent with the specified model
    with console.status(f"[bold green]Initializing Secretary Agent with model: {args.model}...", spinner="dots"):
        secretary_agent = SecretaryAgent(model_name=args.model)
        logger.info(f"Secretary Agent initialized with model: {args.model}")
    
    # Get the last email update time
    last_update = get_initial_update_time()
    
    # Display initial status
    display_status(last_update, AppUser.email)
    
    try:
        # Main processing loop
        while True:
            last_update = process_emails(gmail_handler, secretary_agent, last_update, args)
    
    except KeyboardInterrupt:
        logger.info("Shutting down Clara AI")
        console.print("\n[bold yellow]Shutting down Clara AI...[/bold yellow]")
        console.print("[green]Thank you for using Clara AI![/green]")


if __name__ == "__main__":
    main()