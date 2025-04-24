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
for all email operations while storing user details and last email update times in Azure CosmosDB.
"""
import json
import logging
import argparse
import pickle
import signal
import sys
import time
import traceback
import os
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn, TimeRemainingColumn
from rich.table import Table
from rich import print as rprint
from tqdm import tqdm
from agents.secretary_agent import SecretaryAgent
from objects.gmail_handler import GmailHandler
from user import AppUser
from datetime import datetime, timedelta, timezone
from agents.email_response import EmailResponse
from helpers import get_threads_require_process, process_thread
from cosmos_db import CosmosDB


# Create console instance for rich output
console = Console()

def setup_logging(debug=False, log_file="clara_secretary.log"):
    """Set up logging with optional rich formatting for console output"""
    level = logging.DEBUG if debug else logging.INFO
    
    # Configure basic file logging
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    
    # Configure rich console logging
    rich_handler = RichHandler(rich_tracebacks=True, console=console)
    
    # Set up the logger
    logger = logging.getLogger("ClaraSecretary")
    logger.setLevel(level)
    logger.handlers = [file_handler, rich_handler]  # Replace any existing handlers
    
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
    parser.add_argument('--limit', type=int, default=5,
                        help='Maximum number of emails to fetch')
    
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
    logger = logging.getLogger("ClaraSecretary")
    logger.warning("Received exit signal. Shutting down Clara Secretary...")
    sys.exit(0)

def main():
    # Set up signal handlers for graceful exit
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)
    
    # Parse arguments
    args = parse_arguments()
    
    # Display welcome banner
    display_banner()
    
    # Set up logging
    logger = setup_logging(args.debug, args.log_file)
    
    # Initialize CosmosDB for user management
    with console.status("[bold green]Connecting to Azure CosmosDB...", spinner="dots"):
        try:
            cosmos_db = CosmosDB.get_instance()
            logger.info("Connected to Azure CosmosDB for user management")
        except Exception as e:
            logger.error(f"Failed to connect to Azure CosmosDB: {e}")
            console.print("[bold red]Error: Failed to connect to Azure CosmosDB[/bold red]")
            exit(1)
    
    # Authenticate with Gmail 
    with console.status("[bold green]Authenticating with Gmail...", spinner="dots"):
        user_login_method = 'gmail'
        gmail_handler = GmailHandler()
    
    # Make sure we have a valid user email
    if not AppUser.email:
        logger.error("Error: Could not determine user email from Gmail authentication")
        console.print("[bold red]Error: Could not determine user email from Gmail authentication[/bold red]")
        exit(1)
    
    logger.info(f"Using authenticated user: {AppUser.email}")
    
    # Load or create user profile in CosmosDB
    with console.status("[bold green]Loading user profile from CosmosDB...", spinner="dots"):
        user_exists = AppUser.load_from_db(AppUser.email)
        if not user_exists:
            logger.info(f"Creating new user profile for {AppUser.email}")
            AppUser.save_to_db()
        else:
            logger.info(f"Loaded existing user profile for {AppUser.email}")
    
    # Initialize the SecretaryAgent
    with console.status("[bold green]Initializing Secretary Agent...", spinner="dots"):
        secretary_agent = SecretaryAgent()
    
    # Get the last email update time from CosmosDB
    with console.status("[bold green]Getting last email update time from CosmosDB...", spinner="dots"):
        last_update = AppUser.get_last_email_update_time()
        if last_update:
            try:
                last_update = datetime.fromisoformat(last_update)
                logger.info(f"Last Email Update: {last_update} | {last_update.timestamp()}")
            except ValueError:
                logger.warning(f"Invalid last update time format in database: {last_update}")
                last_update = None
        else:
            logger.info("Last Email Update: Not Initialized")
    
    # Display initial status
    display_status(last_update, AppUser.email)
    
    try:
        while True:
            try:
                # Fetch threads with integrated analysis
                if user_login_method == 'gmail':
                    query = 'category:primary'
                    if last_update:
                        # Get the timestamp directly from last_update
                        timestamp_seconds = int(last_update.timestamp()) + 15
                        
                        # Use the timestamp directly in the query
                        query += f" after:{timestamp_seconds}"
                        
                        logger.info(f"Query: {query} (timestamp from: {last_update.isoformat()})")
                    
                    with console.status(f"[bold green]Fetching emails with query: {query}...", spinner="dots"):
                        all_threads = gmail_handler.fetch_threads( 
                            user_id='me', 
                            query=query, 
                            limit=args.limit,
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
                    
                    # Process threads that need attention
                    threads_require_process = get_threads_require_process(all_threads)
                    
                    if threads_require_process:
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
                    
                    # Update timestamp from the latest thread if available
                    if all_threads:
                        min_datetime = datetime.min.replace(tzinfo=timezone.utc)
                           # Function to safely get last_updated with consistent timezone
                        def get_safe_datetime(thread):
                            if not thread.last_updated:
                                return min_datetime
                            else:
                                # If it already has timezone info, convert to UTC
                                return thread.last_updated.astimezone(timezone.utc)
                        
                        newest_thread = max(all_threads, key=get_safe_datetime)
                        last_update = newest_thread.last_updated
                        
                        # Ensure last_update is a datetime object
                        if last_update and isinstance(last_update, str):
                            try:
                                # Try to parse ISO format first
                                last_update = datetime.fromisoformat(last_update)
                            except ValueError:
                                try:
                                    # Fallback to a more lenient parser
                                    last_update = datetime.strptime(last_update, "%Y-%m-%d %H:%M:%S.%f%z")
                                except ValueError:
                                    # If all parsing fails, keep the previous last_update value
                                    logger.warning(f"Could not parse last_update string: {last_update}. Keeping previous value.")
                        
                        # Get the current last update time from CosmosDB
                        current_db_time = AppUser.get_last_email_update_time()
                        if current_db_time:
                            try:
                                current_datetime = datetime.fromisoformat(current_db_time)
                                # Only update if the new time is later than the current stored time
                                if last_update > current_datetime:
                                    AppUser.update_last_email_time(last_update)
                                    logger.info(f"Updated last_update time to {last_update} | {last_update.timestamp()}")
                            except ValueError:
                                # If we can't parse the current time, just update
                                AppUser.update_last_email_time(last_update)
                                logger.info(f"Updated last_update time to {last_update} | {last_update.timestamp()}")
                        else:
                            # If no current time stored, update
                            AppUser.update_last_email_time(last_update)
                            logger.info(f"Updated last_update time to {last_update} | {last_update.timestamp()}")
                
                next_check_time = datetime.now() + timedelta(seconds=args.interval)
                logger.info(f"Waiting until next check ({next_check_time.strftime('%H:%M:%S')})")
                
                # Countdown timer for next check
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[bold green]Next check in:[/bold green]"),
                    BarColumn(),
                    TimeRemainingColumn(),
                    console=console
                ) as progress:
                    wait_task = progress.add_task("Waiting", total=args.interval)
                    remaining_time = args.interval
                    
                    while remaining_time > 0:
                        time.sleep(1)
                        remaining_time -= 1
                        progress.update(wait_task, completed=args.interval - remaining_time)
                
            except Exception as e:
                logger.error(f"Error in main processing loop: {e}")
                logger.debug(traceback.format_exc())
                console.print(f"[bold red]Error encountered: {e}[/bold red]")
                logger.warning(f"Retrying in 60 seconds...")
                console.print("[yellow]Retrying in 60 seconds...[/yellow]")
                time.sleep(60)  

    except KeyboardInterrupt:
        logger.info("Shutting down Clara AI")
        console.print("\n[bold yellow]Shutting down Clara AI...[/bold yellow]")
        console.print("[green]Thank you for using Clara AI![/green]")


if __name__ == "__main__":
    main()