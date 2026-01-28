from langchain.agents import create_agent
from rag_utils import load_existing_vectorstore, ollama_llm
from langchain.tools import tool
from pii_utils import redact_pii, detect_pii
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from rich import box
import textwrap

# Initialize Rich console
console = Console()

legal_vector_store = load_existing_vectorstore()

def create_retrieve_context_tool(activate_pii_detector: bool = True):
    """Create the retrieve_context tool with optional PII protection"""
    
    @tool(response_format="content_and_artifact")
    def retrieve_context(query: str):
        """Retrieve information to help answer a query with optional PII protection."""
        
        if activate_pii_detector:
            # Redact PII from query before processing
            safe_query, detected_pii = redact_pii(query, strategy="redact")
            
            if detected_pii:
                console.print(
                    Panel(
                        f"🔒 [yellow]PII Protection:[/yellow] {len(detected_pii)} sensitive items detected and redacted\n"
                        f"📋 [yellow]Types:[/yellow] {[entity['label'] for entity in detected_pii]}",
                        title="🛡️ Privacy Guard Active",
                        title_align="left",
                        border_style="yellow"
                    )
                )
        else:
            safe_query = query
            console.print(
                Panel(
                    "🔓 [green]PII Protection:[/green] Privacy guard is currently disabled",
                    title="⚡ Fast Mode",
                    title_align="left",
                    border_style="green"
                )
            )
        
        retrieved_docs = legal_vector_store.similarity_search(safe_query, k=2)
        
        # Process retrieved documents with optional PII protection
        processed_docs = []
        for doc in retrieved_docs:
            if activate_pii_detector:
                safe_content, doc_pii = redact_pii(doc.page_content, strategy="redact")
                processed_docs.append({
                    'original_content': doc.page_content,
                    'safe_content': safe_content,
                    'pii_detected': doc_pii,
                    'metadata': doc.metadata
                })
            else:
                processed_docs.append({
                    'original_content': doc.page_content,
                    'safe_content': doc.page_content,  # No redaction
                    'pii_detected': [],
                    'metadata': doc.metadata
                })
        
        serialized = "\n\n".join(
            (f"Source: {doc['metadata']}\nContent: {doc['safe_content']}")
            for doc in processed_docs
        )
        
        return serialized, processed_docs
    
    return retrieve_context

def create_agent_with_pii_option(activate_pii_detector: bool = True):
    """Create an agent with optional PII protection"""
    
    tools = [create_retrieve_context_tool(activate_pii_detector)]
    
    prompt = (
        "YOU ARE LEGALGUARD AI - a specialized legal document analysis assistant. "
        "YOU SHOULD ALWAYS ANSWER IN THE USER'S LANGUAGE (ENGLISH or FRENCH). "
        "YOUR RESPONSE SHOULD ALWAYS BE CLEAR AND CONCISE."
        "You have access to a tool that retrieves context from different legal documents. "
        "Use this tool to provide accurate and relevant answers to user queries based on the retrieved context. "
    )
    
    # Add privacy notice only if PII protection is active
    if activate_pii_detector:
        prompt += (
            "Be aware that sensitive information may be redacted for privacy protection. "
            "IMPORTANT: When you see [REDACTED_XXX] in the content, it means sensitive information has been removed, "
            "and you should inform the user about the redaction for privacy reasons. "
        )
    
    prompt += (
        "ONLY when the answer requires answers from the documents , format your answers using clear markdown-style formatting with proper structure, headers, and bullet points.\n\n"
        
        "RESPONSE FORMATTING GUIDELINES:\n"
        "# Main Title\n"
        "Brief executive summary\n\n"
        
        "## Key Findings\n"
        "- **Finding 1**: Explanation with important terms in bold\n"
        "- **Finding 2**: Use *italics* for emphasis\n"
        "- **Finding 3**: Clear, actionable insights\n\n"
        
        "## Document Evidence\n"
        "Reference specific documents and sections that support your analysis\n\n"
    )
    
    # Conditionally include privacy notice in guidelines
    if activate_pii_detector:
        prompt += (
            "## Privacy Notice\n"
            "ℹ️ Some information has been redacted (`[REDACTED_XXX]`) to protect personal and sensitive data "
            "in compliance with privacy regulations.\n\n"
        )
    
    
    return create_agent(ollama_llm, tools, system_prompt=prompt)

def create_document_table(docs, activate_pii_detector: bool):
    """Create a beautiful table showing document sources"""
    table = Table(show_header=True, header_style="bold magenta", box=box.ROUNDED)
    table.add_column("📄 Document", style="cyan", width=20)
    table.add_column("📝 Type", style="green")
    table.add_column("🔍 Pages", style="yellow")
    table.add_column("💾 Source", style="blue")
    table.add_column("🛡️ PII Status", style="red" if activate_pii_detector else "green")
    
    for doc in docs:
        source = doc['metadata'].get('source', 'Unknown')
        doc_type = "PDF" if source.endswith('.pdf') else "Text"
        pages = f"{doc['metadata'].get('page', 0) + 1}/{doc['metadata'].get('total_pages', 1)}"
        
        # Shorten source path for display
        display_source = source.split('/')[-1] if '/' in source else source
        
        # PII status
        pii_status = "Protected" if activate_pii_detector else "Visible"
        
        table.add_row(
            f"Document {len(table.rows) + 1}",
            doc_type,
            pages,
            display_source,
            pii_status
        )
    
    return table

def truncate_content(content: str, max_lines: int = 15) -> str:
    """Intelligently truncate content while preserving structure"""
    lines = content.split('\n')
    if len(lines) <= max_lines:
        return content
    
    truncated = '\n'.join(lines[:max_lines])
    return truncated + f"\n\n[yellow]... [content truncated - {len(lines) - max_lines} lines omitted][/yellow]"

def pretty_print_rich(event, activate_pii_detector: bool):
    """Rich-based pretty printing with professional formatting"""
    message = event["messages"][-1]
    
    if hasattr(message, 'type'):
        if message.type == 'human':
            console.print(
                Panel(
                    message.content,
                    title="👤 Human Query",
                    title_align="left",
                    border_style="green",
                    style="white"
                )
            )
            
        elif message.type == 'ai':
            if hasattr(message, 'tool_calls') and message.tool_calls:
                # Thinking and tool usage
                tool_info = "\n".join(
                    f"• [cyan]{tool_call['name']}[/cyan] with args: {tool_call['args']}"
                    for tool_call in message.tool_calls
                )
                
                mode_indicator = "🛡️ Privacy Mode" if activate_pii_detector else "⚡ Fast Mode"
                
                console.print(
                    Panel(
                        tool_info,
                        title=f"🧠 LegalGuard AI - {mode_indicator}",
                        title_align="left",
                        border_style="blue",
                        style="white"
                    )
                )
            else:
                # Final answer with markdown
                markdown_content = Markdown(message.content)
                mode_indicator = "Privacy-First Analysis" if activate_pii_detector else "Full-Data Analysis"
                
                console.print(
                    Panel(
                        markdown_content,
                        title=f"💎 LegalGuard AI - {mode_indicator}",
                        title_align="left",
                        border_style="magenta",
                        style="white"
                    )
                )
                
        elif message.type == 'tool':
            # Tool results with document table and content
            try:
                # Parse the returned data
                content, docs = message.content if isinstance(message.content, tuple) else (message.content, [])
                
                # Create document overview table
                if docs:
                    console.print(
                        Panel(
                            create_document_table(docs, activate_pii_detector),
                            title="📊 Retrieved Documents",
                            title_align="left",
                            border_style="yellow"
                        )
                    )
                
                # Show truncated content with syntax highlighting
                truncated_content = truncate_content(str(content))
                syntax = Syntax(
                    truncated_content,
                    "text",
                    theme="monokai",
                    line_numbers=True,
                    word_wrap=True
                )
                
                console.print(
                    Panel(
                        syntax,
                        title=f"🔧 Tool Results: {message.name}",
                        title_align="left",
                        border_style="yellow"
                    )
                )
                
            except (ValueError, TypeError):
                # Fallback for non-tuple content
                truncated_content = truncate_content(str(message.content))
                console.print(
                    Panel(
                        truncated_content,
                        title=f"🔧 Tool Results: {message.name}",
                        title_align="left",
                        border_style="yellow"
                    )
                )

def print_welcome_banner(activate_pii_detector: bool):
    """Print a beautiful welcome banner with mode indicator"""
    mode_text = "🛡️ PRIVACY MODE" if activate_pii_detector else "⚡ FAST MODE"
    mode_style = "bold magenta" if activate_pii_detector else "bold green"
    
    banner_text = Text()
    banner_text.append(" LEGALGUARD AI ", style="bold white on black")
    banner_text.append("\nLegal Document Analysis System\n", style="bold cyan")
    banner_text.append(f"{mode_text}", style=mode_style)
    banner_text.append("\nAI-Powered • Professional", style="green")
    
    console.print(
        Panel(
            banner_text,
            box=box.DOUBLE,
            border_style="magenta" if activate_pii_detector else "green",
            padding=(1, 2)
        )
    )

def answer_query(query: str, activate_pii_detector: bool = True):
    """Answer a user query using the RAG agent with optional PII protection.
    
    Args:
        query: The user's question
        activate_pii_detector: If True, enables PII protection and redaction.
                              If False, processes data without privacy protection.
    """
    
    print_welcome_banner(activate_pii_detector)
    
    # Create agent with the specified PII setting
    agent = create_agent_with_pii_option(activate_pii_detector)
    
    # Apply PII protection to query if enabled
    if activate_pii_detector:
        safe_query, pii_entities = redact_pii(query, strategy="redact")
        if pii_entities:
            console.print(
                Panel(
                    f"🔒 [yellow]PII Protection:[/yellow] {len(pii_entities)} sensitive items detected and redacted\n"
                    f"📋 [yellow]Types:[/yellow] {[entity['label'] for entity in pii_entities]}",
                    title="🛡️ Privacy Guard Active",
                    title_align="left",
                    border_style="yellow"
                )
            )
    else:
        safe_query = query
        # Optional: Still detect PII for informational purposes, but don't redact
        pii_entities = detect_pii(query)
        if pii_entities:
            console.print(
                Panel(
                    f"🔓 [green]PII Detection Only:[/green] {len(pii_entities)} sensitive items found (not redacted)\n"
                    f"📋 [green]Types:[/green] {[entity['label'] for entity in pii_entities]}",
                    title="🔍 PII Visibility Mode",
                    title_align="left",
                    border_style="green"
                )
            )
    
    try:
        with console.status("[bold green]Analyzing legal documents...", spinner="dots"):
            for event in agent.stream(
                {"messages": [{"role": "user", "content": safe_query}]},
                stream_mode="values",
            ):
                pretty_print_rich(event, activate_pii_detector)
                
    except Exception as e:
        console.print(
            Panel(
                f"[red]Error: {str(e)}[/red]",
                title="❌ System Error",
                title_align="left",
                border_style="red"
            )
        )
        import traceback
        console.print(Syntax(traceback.format_exc(), "python", theme="monokai"))

# Example usage and testing
if __name__ == "__main__":
    # Test with PII protection ON (default)
    console.print("\n" + "="*60)
    console.print("[bold]TEST 1: With PII Protection[/bold]")
    console.print("="*60)
    answer_query(
        "what is the capital of TechCorp?", 
        activate_pii_detector=False
    )
