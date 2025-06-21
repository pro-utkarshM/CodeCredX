# flow.py
from pocketflow import Flow
# Import all necessary nodes
from nodes import ResumeInputNode, URLExtractionNode, GitHubAnalyzerNode, LLMSummarizerNode

def create_codecredx_flow():
    """
    Creates and returns the CodeCredX flow,
    now including GitHub analysis and LLM summarization.
    """
    print("Creating CodeCredX flow...")

    # Initialize all nodes for the current phases
    resume_input_node = ResumeInputNode()
    url_extraction_node = URLExtractionNode()
    github_analyzer_node = GitHubAnalyzerNode()
    llm_summarizer_node = LLMSummarizerNode()

    # Define the sequence of nodes explicitly.
    # The '>>' operator in PocketFlow is meant to chain them.
    # This ensures that after resume_input_node's post method completes,
    # the flow proceeds to url_extraction_node, and so on.
    resume_input_node >> url_extraction_node
    url_extraction_node >> github_analyzer_node
    github_analyzer_node >> llm_summarizer_node

    # The flow starts with the ResumeInputNode.
    return Flow(start=resume_input_node)

# Create an instance of the flow for direct import if needed
codecredx_flow = create_codecredx_flow()
